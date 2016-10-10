# Standard library imports
from __future__ import absolute_import # So that python knows which celery to import
import os
from datetime import date
import subprocess

# Third party imports
import sqlalchemy
from sqlalchemy.engine.url import make_url # Used to parse database information from env variable
from celery import shared_task
import boto3

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
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
    # TODO change line endings to accept \r\n as well, if necessary
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
    return [headers, data]

@shared_task
def write_originals_to_s3():
    # Access S3 bucket using credentials in ~/.aws/credentials
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

    # Write the file to Amazon S3
    bucket.put_object(Key='{db_name}/{today}-{table}/original/{filename}.csv'.format(
        db_name = db_name, 
        today = date.today().isoformat(),
        table = table_name,
        filename = table_name), Body=fcontent)

    # Generate a README file
    readme_template = open(os.path.join(settings.BASE_DIR, 'readme_template'), 'r').read()
    readme = readme_template.format(topic=topic.upper(), 
            div='=' * len(topic),
            reporter=reporter_name, 
            aq=next_aquisition, 
            owner=owner, 
            contact=press_contact,
            number=press_contact_number,
            email=press_contact_email)

    # Write the README to the S3 bucket
    bucket.put_object(Key='{db_name}/{today}-{table}/README.txt'.format(
        db_name = db_name, 
        today = date.today().isoformat(),
        table = table_name), Body=readme)

    logging.info('File written to S3 bucket')
    return
