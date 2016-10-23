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
from sqlalchemy.engine.url import make_url
from celery import shared_task
from celery.contrib import rdb
import boto3

# Local module imports
from .utils import get_column_types

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ['DATA_WAREHOUSE_URL']

#---------------------------------------
# A celery task that accesses a dataabse
# and executes a LOAD DATA INFILE query
# to load the csv into it.
#---------------------------------------
@shared_task(bind=True)
def load_infile(self, path, delimiter, db_name, table_name, columns):
    step = 0

    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    # Keep track of progress
    step += 1
    self.update_state(state='PENDING', meta={'error': False, 'current': step, 'total': 4})

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in columns]
    sql_args = {
        'table': table_name,
        'columns': (',').join(stypes),
        'path': path,
        'db': db_name,
        'delimiter': delimiter,
        'time': time.time() # For debugging purposes only
    }

    # Keep track of PENDING
    step += 1
    self.update_state(state='PENDING', meta={'error': False, 'current': step, 'total': 4})

    # TODO change line endings to accept \r\n as well, if necessary
    print 'CREATE TABLE {table} ({columns})'.format(**sql_args)
    query = """
        CREATE TABLE {table} ({columns});
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)

    sql_warnings = []

    # Record all warnings raised by the writing to the MySQL db. SQLAlchemy doesn't
    # always raise exceptions for data loss
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')

        # Check if a database with the given name exists. If it doesn't, create one.
        # If a SQL error is thrown, end the process and return a summary of the error
        try:
            connection.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
            connection.execute('USE {}'.format(db_name))
            connection.execute(query)
        except exc.SQLAlchemyError as e:
            r = re.compile(r'\(.+?\)')
            return {'error': True, 'errorMessage': r.findall(str(e))[1]} 

        # Write warnings to a list for that will be returned to the user
        if len(w) > 0:
            sql_warnings = [str(warning) for warning in w]

    step += 1
    self.update_state(state='PENDING', meta={'error': False, 'current': step, 'total': 4})

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    data = connection.execute('SELECT * FROM {db}.{table}'.format(**sql_args))

    dataf = []
    dataf.append([x for x in data.keys()])
    dataf.extend([list(value) for key, value in enumerate(data) if key < 5])

    step += 1
    self.update_state(state='PENDING', meta={'error': False, 'current': step, 'total': 4})

    return {'error': False, 'data': dataf, 'warnings': sql_warnings}

