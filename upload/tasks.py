# Standard library imports
from __future__ import absolute_import
import os
import re
import csv
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
# to load the csv into it
#---------------------------------------
@shared_task(bind=True)
def load_infile(self, path, delimiter, db_name, table_name):
    step = 0

    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    # Keep track of progress
    step += 1
    self.update_state(state='PROGRESS', meta={'error': False, 'current': step, 'total': 4})

    # Check if a database with the given name exists. If it doesn't, create one.
    connection.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
    connection.execute('USE {}'.format(db_name))

    column_types = get_column_types(path)

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in column_types]
    sql_args = {
        'table': table_name,
        'columns': (',').join(stypes),
        'path': path,
        'db': db_name,
        'delimiter': delimiter
    }

    # Keep track of progress
    step += 1
    self.update_state(state='PROGRESS', meta={'error': False, 'current': step, 'total': 4})

    # TODO change line endings to accept \r\n as well, if necessary
    query = r"""
        CREATE TABLE {table} ({columns});
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)

    # Catch any operational errors and send the text of the error to the user
    try:
        connection.execute(query)
    except exc.SQLAlchemyError as e:
        r = re.compile(r'\(.+?\)')
        return {'error': True, 'errorMessage': r.findall(str(e))[1]}

    step += 1
    self.update_state(state='PROGRESS', meta={'error': False, 'current': step, 'total': 4})

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    data = connection.execute('SELECT * FROM {db}.{table}'.format(**sql_args))

    dataf = []
    dataf.append([x for x in data.keys()])
    dataf.extend([list(value) for key, value in enumerate(data) if key < 5])

    step += 1
    self.update_state(state='PROGRESS', meta={'error': False, 'current': step, 'total': 4})

    return dataf

