# Standard library imports
from __future__ import absolute_import
import os
import re
import warnings

# Third party imports
import sqlalchemy
from sqlalchemy import exc # error handling
from celery import shared_task
import boto3
import botocore
from csvkit import sql, table

# Local module imports
from .utils import S3Manager

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ.get('DATA_WAREHOUSE_URL')  # Where the table will be uploaded
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
TOTAL = 10 # Unfortunately we have to hardcode the total number of progress steps


class ProgressTracker(object):
    """
    This module sends messages to the Redis server to update the state of the
    task so that we can have an informative, pretty progress bar
    """
    def __init__(self, celery):
        self.celery = celery
        self.total = TOTAL
        self.step = 0

    def forward(self, message):
        self.step += 1
        meta = {'message': message,
                'error': False,
                'current': self.step,
                'total': self.total}
        self.celery.update_state(state='PROGRESS', meta=meta)


class Loader(object):
    """
    This module handles creation of all the queries necessary to create a table
    and load local data into it, all while sending progress updates to a celery
    class instance
    """
    def __init__(self, tracker, table, columns, path):
        self.tracker = tracker
        self.path = path
        self.table = table
        self.columns = columns

        # Create a connection to the data warehouse. Pass local_infile as a
        # parameter so that the connection will accept LOAD INFILE statements
        engine = sqlalchemy.create_engine(URL + '?local_infile=1')
        self.connection = engine.connect()

    def _get_column_types(self):
        self.tracker.forward('Inferring datatype of columns')
        # Load the csv and use csvkit's sql.make_table utility 
        # to infer the datatypes of the columns.
        with open(self.path,'r') as f:
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

            self.columns[i]['datatype'] = clean_type.lower()
            self.columns[i]['raw_type'] = raw_type
            self.columns[i]['length'] = clean_length

    def _make_create_table_q(self):
        """
        Generate a CREATE TABLE query that casts each column as the right type
        """
        self._get_column_types()

        # Convert column types back to strings for use in the create table
        # statement
        types= ['{name} {raw_type}'.format(**x) for x in self.columns]
        args = {'table': self.table, 'columns': (', ').join(types)}
        query = 'CREATE TABLE imports.{table} ({columns});'.format(**args)

        return query

    def _make_load_table_q(self):
        # We've sanitized inputs to avoid risk of SQL injection. To understand
        # of why we're sanitizing manually instead of passing args to 
        # sqlalchemy's execute method, see:
        # http://stackoverflow.com/q/40249590/4599578
        query = """
            LOAD DATA LOCAL INFILE "{path}" INTO TABLE imports.{table}
            FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
            IGNORE 1 LINES;
            """.format(path=self.path, table=self.table)

        return query

    def run_load_infile(self):
        """
        The only public method of this class

        Creates a table in MySQL database and uploads a CSV to it

        Record all warnings raised by writing to the MySQL DB. MySQL doesn't
        always raise exceptions for data truncation (?!)
        """
        sql_warnings = []
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            create_table_query = self._make_create_table_q()
            load_data_query = self._make_load_table_q()

            # If an SQL error is thrown, end the process and return a summary
            # of the error
            try:
                self.tracker.forward('Creating table in imports database')
                self.connection.execute(create_table_query)

                # Execute load data infile statement
                self.tracker.forward('Executing load data infile')
                self.connection.execute(load_data_query)

            # Use the general class that catches all sqlalchemy errors.
            # Store only the relevant part of the warnings
            except exc.SQLAlchemyError as e:
                r = re.compile(r'\(.+?\)')
                return {'error': True, 'errorMessage': r.findall(str(e))[1]} 

            if len(w) > 0:
                r = re.compile(r'\(.+?\)')
                sql_warnings = [r.findall(str(warning))[0] for warning in w]

        return (create_table_query, sql_warnings)

    def get_preview(self):
        return self.connection.execute('SELECT * FROM imports.{} LIMIT 5'.format(self.table))

    def end_connection(self):
        self.connection.close()


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
    tracker = ProgressTracker(self)
    tracker.forward('Downloading data from Amazon S3')

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
    tracker.forward('Connecting to MySQL server')

    loader = Loader(tracker, table_name, columns, local_path)
    create_table_query, sql_warnings = loader.run_load_infile()

    # After the file is successfully uploaded to the DB, copy it from the 
    # tmp/ directory to its final home and delete the temporary file
    tracker.forward('Loading the file into S3')
    s3 = S3Manager(local_path, table_name)
    final_s3_path = s3.copy_final_s3(s3_path)

    # Return a preview of the top few rows in the table
    # to check that the casting was correct
    tracker.forward('Querying the table for preview data')
    preview = loader.get_preview()

    # End the MySQL connection
    tracker.forward('Closing the connection to the database')
    loader.end_connection()

    dataf = []
    dataf.append([x for x in preview.keys()])

    return {'error': False,
        'table': table_name,
        'final_s3_path': final_s3_path,
        'data': dataf,
        'headers': columns,
        'warnings': sql_warnings,
        'query': create_table_query
    }

