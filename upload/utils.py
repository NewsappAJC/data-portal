# Python standard lib imports
import os
import re
import pdb # for debugging only
from collections import defaultdict
from celery.contrib import rdb

# Django imports
from django.conf import settings

# Third party imports
from csvkit import sql, table
import boto3
import botocore

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')

#remove quote chars csvkit puts around capitalized column names, change engine to MYISAM
#if routine errors occur, use this to modify the create table statement
#deprecate when we start interactively handling field types
def polish_create_table(create_table):
    create_table=create_table.replace('"','')
    
    create_table=create_table.replace(");",")ENGINE=MYISAM;")
    
    return create_table


#--------------------------------------------
# Helper functions
#--------------------------------------------
def clean(names):
    preexisting = [] # Will keep track of duplicate column names
    clean_names = [] # Will hold all our column names
    for name in names:
        # Append a number to a column if that column name already exists in the table
        if name in preexisting:
            preexisting.append(name)
            c = preexisting.count(name) - 1
            name += str(c)

        # Use regex to remove spaces at the beginning of the string, replace spaces and
        # underscores with hyphens, remove line breaks, strip all non-alphanumeric 
        # characters
        rs = [(re.compile(r'-|\s'), '_'), (re.compile(r'\W'), '')]
        clean_name = name

        for r, sub_ in rs:
            clean_name = re.sub(r, sub_, clean_name.strip())

        # MySQL allows 64 character column names maximum
        clean_names.append(clean_name.lower()[:60])

    return clean_names

#--------------------------------------------
# End helper functions
#--------------------------------------------

#--------------------------------------------
# Get column names and sample data from a CSV
# without loading the whole csv into memory
# for display by the categorize view
#--------------------------------------------
def get_column_names(filepath):
    sample_rows = []

    with open(filepath, 'r') as f:
        # Loop through lines to avoid reading the entire file into memory
        for i, line in enumerate(f):
            linef = line.split(',')
            # Append the first row to the list of headers
            if i == 0:
                columns = linef
            # Only get sample data from the first 3 rows
            elif i < 4:
                sample_rows.append(linef)
            # After 4 lines, stop reading the CSV
            else:
                break

    # Clean the column names to prevent SQL injection
    headers = [{'name': column, 'sample_data': []} for column in clean(columns)]

    # Give each header
    for sample_row in sample_rows:
        for i in range(len(sample_row)):
            headers[i]['sample_data'].append(str(sample_row[i]))

    # Format the sample data for display
    for h in headers:
        h['sample_data'] = (', ').join(h['sample_data']) + ' ...'

    return headers


#--------------------------------------------
# Infer datatypes of the columns in a csv and
# return a list of dicts with the columns names,
# length, and type
#--------------------------------------------
#--------------------------------------------
# Write the original CSV to s3. The s3 task will
# load the data from s3
#--------------------------------------------
def write_originals_to_s3():
    # Access S3 bucket using credentials in ~/.aws/credentials
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY, 
        aws_secret_access_key=settings.AWS_SECRET_KEY
    )

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

def write_tempfile_to_s3(local_path, table_name):
    """
    Write a temporary file to the S3 server. Used to upload a data file so that
    we can later download it and execute LOAD DATA INFILE on it
    """
    # Begin session with S3 server using ./aws/credentials file
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY
    )
    s3 = session.resource('s3')
    bucket = s3.Bucket(BUCKET_NAME)

    total = 3
    s = 0

    # Check if a file with the same name already exists in the
    # S3 bucket, and if so change the name of the upload and try again
    while True:
        s3_path = 'tmp/{name}({s})'.format(name=table_name, s=s)

        try:
            bucket.download_file(s3_path, '/tmp/s3_throwaway')
            s += 1
            continue

        except botocore.exceptions.ClientError:
            break

    bucket.upload_file(local_path, s3_path)

    return s3_path

