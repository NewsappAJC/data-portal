from __future__ import absolute_import
import os
import subprocess

import sqlalchemy
from sqlalchemy.engine.url import make_url # Used to parse database information from env variable
import csvkit
from celery import shared_task

# Constants
URL = os.environ['DATA_WAREHOUSE_URL']

@shared_task
def load_infile(path, db_name, table_name, delimiter=','):
    # Create a connection to the data warehouse 
    engine = sqlalchemy.create_engine(URL + '?local_infile=1')
    connection = engine.connect()

    # Check if a database with the given name exists. If it doesn't, create one.
    # connection.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
    connection.execute('USE {}'.format(db_name))

    # Mock create table query for testing, Jeff's util function for generating the 
    # statement will go here.
    query = r"""
        CREATE TABLE {table} (
            name VARCHAR(8) NOT NULL,
            age INTEGER NOT NULL,
            occupation VARCHAR(9) NOT NULL
        );
        LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
        FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
        IGNORE 1 LINES;
        """.format(path=path,
                db=db_name,
                table=table_name,
                delimiter=delimiter)

    ## Create the table and load in the data
    connection.execute(query)

    # Return a preview of the top few rows in the table
    # to check if the casting is correct. Save data to session
    # so that it can be accessed by other views
    data = connection.execute('SELECT * FROM User_Jcox.{}'.format(table_name))
    headers = data.keys()

