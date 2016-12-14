# Standard library imports
from __future__ import absolute_import
import os
import re
import warnings

# Third party imports
import sqlalchemy
from sqlalchemy import exc # error handling
from sqlalchemy.sql import text # protect from SQL injection
from celery import shared_task
import boto3
import botocore
from csvkit import sql, table

# Local module imports
from .utils import copy_final_s3

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ.get('DATA_WAREHOUSE_URL')
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
SECRET_KEY = os.environ.get('AWS_SECRET_KEY')


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
    Send a msessage to the Redis server updating the state of the task so that
    we can have an informative progress bar
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
def load_infile(self, s3_path, db_name, table_name, columns, **kwargs):
    """
    A celery task that accesses a database and executes a LOAD DATA INFILE 
    query to load the csv into it.
    """
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
        raise ValueError('Unable to download temporary file from S3')

    # Keep track of progress
    step = forward(self, step, 'Connecting to MySQL server', total)

    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    step = forward(self, step, 'Inferring datatype of columns. This can take a while', total)
    columnsf = get_column_types(local_path, columns)

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in columnsf]
    sql_args = {
        'table': table_name,
        'columns': (', ').join(stypes),
        'path': local_path,
        'db': db_name,
    }

    # Sanitize DB input once more. Table name, path, and columns already sanitized
    sql_args['db'] = sanitize(sql_args['db'])

    # TODO change line endings to accept \r\n as well, if necessary
    # We've sanitized inputs to avoid risk of SQL injection. For explanation
    # of why we're sanitizing manually instead of passing args to sqlalchemy's execute method, see
    # http://stackoverflow.com/questions/40249590/sqlalchemy-error-when-adding-parameter-to-string-sql-query
    create_table_query = 'CREATE TABLE {table} ({columns});'.format(**sql_args)
    load_data_query = """
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)


    sql_warnings = []
    # Record all warnings raised by the writing to the MySQL DB. SQLAlchemy doesn't
    # always raise exceptions for data truncation, which is insane!
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')

        # If an SQL error is thrown, end the process and return a summary of the error
        try:
            # Check if a database with the given name exists. If it doesn't, create one.
            step = forward(self, step, 'Connecting to database {}'.format(db_name), total)

            databases = [d[0] for d in connection.execute(text('SHOW DATABASES;'))]
            if db_name not in databases:
                connection.execute('CREATE DATABASE {name}'.format(name=sql_args['db']), total)

            connection.execute('USE {name}'.format(name=sql_args['db']))

            # Create the table. This raises an error if a table with that names
            # already exists in the database
            step = forward(self, step, 'Creating table', total)
            connection.execute(create_table_query)

            # Execute load data infile statement
            step = forward(self, step, 'Executing load data infile', total)
            connection.execute(load_data_query)

        # General class that catches all sqlalchemy errors
        except exc.SQLAlchemyError as e:
            r = re.compile(r'\(.+?\)') # Grab only the relevant part of the warning
            print str(e)
            return {'error': True, 'errorMessage': r.findall(str(e))[1]} 

        # Write warnings to a list for that will be returned to the user
        if len(w) > 0:
            r = re.compile(r'\(.+?\)')
            sql_warnings = [r.findall(str(warning))[0] for warning in w]

    # After the file is successfully uploaded to the DB, copy it from the 
    # tmp/ directory to its final home and delete the temporary file
    final_s3_path = copy_final_s3(s3_path, db_name, table_name)

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    step = forward(self, step, 'Querying the table for preview data', total)
    data = connection.execute('SELECT * FROM {db}.{table}'.format(**sql_args))

    dataf = []
    dataf.append([x for x in data.keys()])
    dataf.extend([list(value) for key, value in enumerate(data) if key < 5])

    return {'error': False,
        'table': table_name,
        'final_s3_path': final_s3_path,
        'db': db_name,
        'data': dataf,
        'headers': columns,
        'warnings': sql_warnings,
        'create_table_query': create_table_query
    }

