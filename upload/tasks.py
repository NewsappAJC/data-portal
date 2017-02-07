# Standard library imports
from __future__ import absolute_import
import os
import re
import warnings
from urlparse import urlparse

# Third party imports
import sqlalchemy
from sqlalchemy import exc # error handling
from celery import shared_task
import boto3
import botocore
from csvkit import sql, table

# Local module imports
from .utils import copy_final_s3

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ.get('DATA_WAREHOUSE_URL')  # Where the table will be uploaded
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
SECRET_KEY = os.environ.get('AWS_SECRET_KEY')

class Index(object):
    """
    This class handles creation of a query to generate an index for a given
    column in a MySQL table
    """
    def __init__(self, table_id, connection):
        self.table_id = table_id
        self.connection = connection

    def _get_columns(self, data_type):
        query = """
        SELECT CONCAT_WS('.','imports',t,'table') AS table,
            CONCAT('`',GROUP_CONCAT(c.`column` SEPARATOR '`,`'),'`') AS index_fields
        FROM data_import_tool.`upload_table` t
        JOIN data_import_tool.`upload_column` c
        ON t.`id`=c.`table_id`
        WHERE RIGHT(c.`information_type`,5) = '{type}'
        AND t.`id`={id}
        GROUP BY 1;
        """.format(id=self.table_id, type=data_type)

        columns = self.connection.execute(query).fetchall()
        return columns

    def get_query(self, data_type):
        indexer = self._get_columns(data_type)
        if indexer:
            args = {
                'table': indexer[0]['table'],
                'columns': indexer[0]['index_fields']
            }
            query = """
                ALTER TABLE {table} ADD FULLTEXT INDEX `name_index` ({columns})
                """.format(**args)
            return query

class Loader(object):
    """
    This class handles creation of all the queries necessary to create a table,
    load local data into it, and generate indices. 
    """
    def __init__(self, inst, step, connection, table, columns, path):
        self.connection = connection
        self.inst = inst
        self.warnings = []

    def _make_table_q(self, table, cols):
        query = 'CREATE TABLE {table} ({columns});'.format(table=table, columns=cols)
        return query

    def _make_indices(self, name):
        index = Index(name)

    def load_infile(self):
        """
        Upload a local CSV to the MySQL database

        Record all warnings raised by writing to the MySQL DB. MySQL doesn't
        always raise exceptions for data truncation (?!), and we need to catch
        that
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            create_table_query = self._make_table_q(self.table, self.columns)

            # If an SQL error is thrown, end the process and return a summary of the error
            try:
                # Check if a database with the given name exists. If it doesn't, create one.
                forward(self.inst, self.step, 'Connecting to database {}'.format(db_name), total)
                self.step += 1

                # Create the table. This raises an error if a table with that name
                forward(self.inst, step, 'Creating table', total)
                self.step += 1
                self.connection.execute(create_table_query)

                # Execute load data infile statement
                step = forward(self.inst, step, 'Executing load data infile', total)
                connection.execute(load_data_query)

            # General class that catches all sqlalchemy errors
            except exc.SQLAlchemyError as e:
                r = re.compile(r'\(.+?\)') # Grab only the relevant part of the warning
                return {'error': True, 'errorMessage': r.findall(str(e))[1]} 

            # Write warnings to a list for that will be returned to the user
            if len(w) > 0:
                r = re.compile(r'\(.+?\)')
                sql_warnings = [r.findall(str(warning))[0] for warning in w]


def get_column_types(filepath, headers):
    # Load the csv and use csvkit's sql.make_table utility 
    # to infer the datatypes of the columns.
    f = open(filepath,'r')
    csv_table = table.Table.from_csv(f, delimiter=',')
    sql_table = sql.make_table(csv_table)

    for i, column in enumerate(sql_table.columns):
        # Clean the type and name values
        raw_type = str(column.type)
        clean_type = re.sub(re.compile(r'\(\w+\)'), '', raw_type)
        
        # Temporary fix for issue #19
        if raw_type == 'BOOLEAN':
            raw_type = 'VARCHAR(10)'

        if raw_type == 'DATETIME':
            # Dumb guess at the maximum length of a datetime field. Find a 
            # better way!
            raw_type = 'VARCHAR(100)'

        parsed_length = re.search(re.compile(r'\((\w+)\)'), raw_type)
        if parsed_length:
            clean_length = int(parsed_length.group(1))
        else:
            clean_length = None

        headers[i]['datatype'] = clean_type.lower()
        headers[i]['raw_type'] = raw_type
        headers[i]['length'] = clean_length

    return headers

def forward(instance, step, message, total):
    """
    Send a message to the Redis server updating the state of the task so that
    we can have an informative, pretty progress bar
    """
    step += 1
    instance.update_state(state='PROGRESS', meta={'message': message,
                                                  'error': False,
                                                  'current': step,
                                                  'total': total})
    return step


def sanitize(string):
    """
    Substitute all non alphanumeric/underscore (_) characters with empty string
    """
    r = re.compile(r'\W')
    return re.sub(r, '', string)


@shared_task(bind=True)
def load_infile(self, s3_path, table_name, columns, **kwargs):
    """
    A celery task that accesses a database and executes a LOAD DATA INFILE 
    query to load a CSV into it.
    """
    # The total number of steps. Used to send progress reports back to the app
    total = 8
    step = forward(self, 0, 'Downloading data from Amazon S3', total)

    session = boto3.Session(aws_access_key_id=ACCESS_KEY, 
                            aws_secret_access_key=SECRET_KEY)
    s3 = session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    # Attempt to download the temporary file from S3
    try:
        local_path = os.path.join('/', s3_path)
        bucket.download_file(s3_path, local_path)
    except botocore.exceptions.ClientError:
        error_message = 'Upload failed. Unable to download temporary file from S3'
        raise ValueError(error_message)

    # Keep track of progress
    step = forward(self, step, 'Connecting to MySQL server', total)

    # Create a connection to the data warehouse. Pass local_infile as a
    # parameter so that the connection will accept LOAD INFILE statements
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    # Get the DB name from the DATA_WAREHOUSE_URL env var. Baffled as to why
    # SQLAlchemy doesn't provide a way to do this from the connection
    db_name = urlparse(str(engine.url)).path.strip('/')

    step = forward(self, step, 'Inferring datatype of columns', total)
    columnsf = get_column_types(local_path, columns)

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in columnsf]
    sql_args = {
        'connection': connection,
        'table': table_name,
        'columns': (', ').join(stypes),
        'path': local_path,
        'db_name': db_name
    }

    table = Table(**sql_args)
    table.load_infile()

    # TODO change line endings to accept \r\n as well, if necessary
    # We've sanitized inputs to avoid risk of SQL injection. For explanation
    # of why we're sanitizing manually instead of passing args to sqlalchemy's execute method, see
    # http://stackoverflow.com/questions/40249590/sqlalchemy-error-when-adding-parameter-to-string-sql-query
    create_table_query = 'CREATE TABLE {table} ({columns});'.format(**sql_args)
    load_data_query = """
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db_name}.{table}
        FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)



    # After the file is successfully uploaded to the DB, copy it from the 
    # tmp/ directory to its final home and delete the temporary file
    final_s3_path = copy_final_s3(s3_path, table_name)

    # Return a preview of the top few rows in the table
    # to check that the casting was correct
    step = forward(self, step, 'Querying the table for preview data', total)
    data = connection.execute('SELECT * FROM {db_name}.{table}'.format(**sql_args))

    dataf = []
    dataf.append([x for x in data.keys()])
    dataf.extend([list(value) for key, value in enumerate(data) if key < 5])

    connection.close()

    return {'error': False,
        'table': table_name,
        'final_s3_path': final_s3_path,
        'data': dataf,
        'db': db_name,
        'headers': columns,
        'warnings': sql_warnings,
        'query': create_table_query
    }

