# Standard library imports
from __future__ import absolute_import
import os
import re
import csv
import warnings
import redis
import time
from datetime import date
import subprocess
import random

# Third party imports
import sqlalchemy
from sqlalchemy import exc # error handling
from sqlalchemy.sql import text # protect from SQL injection
from sqlalchemy.engine.url import make_url
from celery import shared_task
from celery.contrib import rdb
import boto3
import botocore
from csvkit import sql, table

# Local module imports
from .utils import get_column_types

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ['DATA_WAREHOUSE_URL']

#---------------------------------------
# Begin helper functions
#---------------------------------------
def forward(instance, step, message, total):
    step += 1
    instance.update_state(state='PROGRESS', meta={'message': message, 'error': False, 'current': step, 'total': total})
    return step

def sanitize(string):
    r = re.compile(r'\W')
    return re.sub(r, '', string)
#---------------------------------------
# End helper functions
#---------------------------------------

@shared_task(bind=True)
def load_infile(self, path, db_name, table_name, columns, **kwargs):
    """
    A celery task that accesses a dataabse
    and executes a LOAD DATA INFILE query
    to load the csv into it.
    """
    total = 7

    # Keep track of progress
    step = forward(self, 0, 'Connecting to MySQL server')

    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    step = forward(self, step, 'Inferring datatype of columns. This can take a while', total)
    columnsf = get_column_types(path, columns)

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in columnsf]
    sql_args = {
        'table': table_name,
        'columns': (',').join(stypes),
        'path': path,
        'db': db_name,
    }

    # Sanitize DB input once more. Table name, path, and columns already sanitized
    sql_args['db'] = sanitize(sql_args['db'])

    # TODO change line endings to accept \r\n as well, if necessary
    # We've sanitized inputs to avoid risk of SQL injection. For explanation
    # of why we're sanitizing manually instead of passing args to sqlalchemy's execute method, see
    # http://stackoverflow.com/questions/40249590/sqlalchemy-error-when-adding-parameter-to-string-sql-query
    create_table_query = """
        CREATE TABLE {table} ({columns});
        """.format(**sql_args)

    load_data_query = """
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)


    sql_warnings = []
    # Record all warnings raised by the writing to the MySQL db. SQLAlchemy doesn't
    # always raise exceptions for data loss
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')

        # If a SQL error is thrown, end the process and return a summary of the error
        try:
            # Check if a database with the given name exists. If it doesn't, create one.
            step = forward(self, step, 'Connecting to database {}'.format(db_name), total)

            databases = [d[0] for d in connection.execute(text('SHOW DATABASES;'))]
            if db_name not in databases:
                connection.execute('CREATE DATABASE {name}'.format(name=sql_args['db']), total)

            connection.execute('USE {name}'.format(name=sql_args['db']), total)

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

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    step = forward(self, step, 'Querying the table for preview data')
    data = connection.execute('SELECT * FROM {db}.{table}'.format(**sql_args))

    dataf = []
    dataf.append([x for x in data.keys()])
    dataf.extend([list(value) for key, value in enumerate(data) if key < 5])

    return {'error': False,
        'table': table_name,
        'db': db_name,
        'data': dataf,
        'headers': columns,
        'warnings': sql_warnings
    }


@shared_task(bind=True)
def write_tempfile_to_s3(self, table_name, s=0):
    """
    Write a temporary file to the S3 server.
    """
    path = 'tmp/{name}({s})'.format(name=table_name, s=s)
    total = 3
    # Begin session with S3 server using ./aws/credentials file
    session = boto3.Session(profile_name='data_warehouse')
    s3 = session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    # Check if a file with the same name already exists in the
    # S3 bucket, and if so change the name of the upload and try again
    try:
        step = forward(self, 0, 'Checking S3 for file with name {}'.format(path), total)
        bucket.download_file(path, '/tmp/s3_test_file')
        write_to_s3(path, s + 1)
    except botocore.exceptions.ClientError:
        step = forward(self, step, 'Uploading file to S3', total)
        bucket.put_object(Key=path, Body=fcontent)

    step = forward(self, step, 'Success'.format(BUCKET_NAME), total)

    return {'path': path}

def get_from_s3(path):
    """
    Get a file from s3
    """
    session = boto3.Session(profile_name='data_warehouse')
    s3 = session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    # Check if a file with the same name already exists in the
    # S3 bucket, and if so throw an error
    try:
        bucket.download_file(table_name, '/tmp/s3_test_file')
        messages.add_message(request, messages.ERROR, 'A file with that name already exists in s3')
        return render(request, 'upload.html', {'form': form})
    except botocore.exceptions.ClientError:
        pass
