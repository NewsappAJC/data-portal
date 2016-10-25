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

# Local module imports
from .utils import get_column_types

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ['DATA_WAREHOUSE_URL']
TOTAL_STEPS = 7

#---------------------------------------
# Begin helper functions
#---------------------------------------
def forward(instance, step, message):
    step += 1
    instance.update_state(state='PROGRESS', meta={'message': message, 'error': False, 'current': step, 'total': TOTAL_STEPS})
    return step
#---------------------------------------
# End helper functions
#---------------------------------------

#---------------------------------------
# A celery task that accesses a dataabse
# and executes a LOAD DATA INFILE query
# to load the csv into it.
#---------------------------------------
@shared_task(bind=True)
def load_infile(self, path, db_name, table_name, columns, delimiter=',', **kwargs):
    # Keep track of progress
    step = forward(self, 0, 'Connecting to MySQL server')

    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    step = forward(self, step, 'Inferring datatype of columns. This can take a while')
    columnsf = get_column_types(path, columns)

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in columnsf]
    sql_args = {
        'table': table_name,
        'columns': (',').join(stypes),
        'path': path,
        'db': db_name,
        'delimiter': delimiter,
        'time': time.time() # For debugging purposes only
    }

    # TODO change line endings to accept \r\n as well, if necessary
    create_table_query = text("""
        CREATE TABLE :table (:columns);
        """
    )

    load_data_query = text("""
        LOAD DATA LOCAL INFILE ":path" INTO TABLE :db.:table
        FIELDS TERMINATED BY ":delimiter" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """
    )

    sql_warnings = []

    # Record all warnings raised by the writing to the MySQL db. SQLAlchemy doesn't
    # always raise exceptions for data loss
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')

        # If a SQL error is thrown, end the process and return a summary of the error
        try:
            # Check if a database with the given name exists. If it doesn't, create one.
            step = forward(self, step, 'Connecting to database {}'.format(db_name))

            databases = [d[0] for d in connection.execute(text('SHOW DATABASES;'))]
            rdb.set_trace()
            if db_name not in databases:
                connection.execute(text('CREATE DATABASE :name;'), {'name': db_name})

            connection.execute(text('USE :name;'), {'name': db_name})

            # Create the table. This raises an error if a table with that names
            # already exists in the database
            step = forward(self, step, 'Creating table')
            connection.execute(create_table_query, **sql_args)

            # Execute load data infile statement
            step = forward(self, step, 'Executing load data infile')
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
    data = connection.execute('SELECT * FROM :db.:table', **sql_args)

    dataf = []
    dataf.append([x for x in data.keys()])
    dataf.extend([list(value) for key, value in enumerate(data) if key < 5])

    return {'error': False, 'data': dataf, 'headers': columns, 'warnings': sql_warnings}

