# Standard library imports
from __future__ import absolute_import
import os
import csv
from time import time
import pdb
from datetime import date
import subprocess
import random

# Third party imports
import sqlalchemy
from sqlalchemy.engine.url import make_url
from celery import shared_task
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
@shared_task
def load_infile(db_name, table_name, path, delimiter=','):
    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

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

    # Mock create table query for testing, Jeff's util function for generating the 
    # statement will go here.
    # TODO change line endings to accept \r\n as well, if necessary
    query = r"""
        CREATE TABLE {table} ({columns});
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)

    ## Create the table and load in the data
    connection.execute(query)

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    data = connection.execute('SELECT * FROM {db}.{table}'.format(**sql_args))
    headers = data.keys()
    return [headers, data]


def load_infile_debug(db_name='user_cox', delimiter=','):
    test_dict = {'name': 'Jonathan', 'age': 24, 'occupation': 'developer'}
    path = '/tmp/django_import_test.csv'

    with open(path, 'w') as f:
        w = csv.DictWriter(f, test_dict.keys())
        w.writeheader()
        w.writerow(test_dict)

    random_table = 'test{}'.format(int(random.random() * 1000))

    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    # Check if a database with the given name exists. If it doesn't, create one.
    connection.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
    connection.execute('USE {}'.format(db_name))

    column_types = get_column_types(path)

    # Convert column types back to strings for use in the create table statement
    stypes = ['{name} {raw_type}'.format(**x) for x in column_types]
    sql_args = {
        'table': random_table,
        'columns': (',').join(stypes),
        'path': path,
        'db': db_name,
        'delimiter': delimiter
    }
    # Mock create table query for testing, Jeff's util function for generating the 
    # statement will go here.
    # TODO change line endings to accept \r\n as well, if necessary
    query = r"""
        CREATE TABLE {table} ({columns});
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(**sql_args)

    ## Create the table and load in the data
    connection.execute(query)

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    data = connection.execute('SELECT * FROM {db}.{table}'.format(**sql_args))
    dataf = [value for key, value in enumerate(data) if key < 5]
    headers = data.keys()
    print dataf, headers

    return [headers, dataf]
