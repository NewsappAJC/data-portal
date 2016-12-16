# Python standard lib imports
import os
from datetime import date
import re

# Django imports
from django.conf import settings

# Third party imports
import boto3
import botocore

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')


def start_s3_session():
    """
    Use boto3 to start an s3 session
    """
    session = boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY
    )

    s3 = session.resource('s3')

    return s3


def check_duplicates(key, i=0):
    """
    Check if a key already exists in S3. If it does, generate a new key and
    return it
    """
    try:
        # Boto3 doesn't have a method to check if a given key already exists.
        # Trying to get metadata and catching the resulting ClientError
        # is the least expensive way to do it
        client = boto3.client('s3',
                              aws_access_key_id=settings.AWS_ACCESS_KEY,
                              aws_secret_access_key=settings.AWS_SECRET_KEY)

        client.head_object(Bucket=BUCKET_NAME, Key=key)

        # If the key already exists, call the function again with a different
        # suffix
        i += 1

        # If there's already a number appended to the end of the key, strip it
        # out so we can append the new number
        rx = re.compile(r'\(\d+\)$')
        if rx.search(key):
            key = re.sub(rx, '', key)

        return check_duplicates('{}({})'.format(key, str(i)), i)
    except botocore.exceptions.ClientError:
        return key


def clean(names):
    """
    Parse non-alphanumeric symbols out of headers, and append a number
    to the end of the column name in the case of duplicates
    """
    preexisting = []  # Will keep track of duplicate column names
    clean_names = []  # Will hold sanitized column names
    for name in names:
        # Append a number to a column name if it already exists in the table
        preexisting.append(name)

        if preexisting.count(name) > 1:
            c = preexisting.count(name) - 1
            name += str(c)

        # Use regex to remove spaces at the beginning of the string, replac
        # spaces and underscores with hyphens, remove line breaks, strip all
        # non-alphanumeric characters
        rxs = [(re.compile(r'-|\s'), '_'), (re.compile(r'\W'), '')]
        clean_name = name

        for rx, sub_ in rxs:
            clean_name = re.sub(rx, sub_, clean_name.strip())

        # MySQL allows 64 character column names maximum
        clean_names.append(clean_name.lower()[:60])

    return clean_names


def get_column_names(filepath):
    """
    Get column names and sample data from a CSV without loading the whole csv
    into memory
    """
    sample_rows = []
    with open(filepath, 'r') as f:
        # Loop through lines to avoid reading the entire file into memory
        for i, line in enumerate(f):
            # Split lines on commas. TODO handle other delimiters
            linef = line.split(',')
            # Generate our list of headers from the first row
            if i == 0:
                columns = linef
            # Only get sample data from the first 3 rows
            elif i < 4:
                sample_rows.append(linef)
            # After 4 lines, stop reading the CSV
            else:
                break

    # Clean the column names to prevent SQL injection
    ccolumns = clean(columns)
    headers = [{'name': column, 'sample_data': []} for column in ccolumns]

    # Append the sample data to the header objects
    for sample_row in sample_rows:
        for i in range(len(sample_row)):
            headers[i]['sample_data'].append(str(sample_row[i]))

    return headers


def copy_final_s3(tmp_path, table_name):
    """
    Copy the original CSV file from the tmp bucket to its permanent home on s3
    """
    s3 = start_s3_session()

    # Compose a key name
    today = date.today().isoformat()
    stem = '{today}_{table}'.format(table=table_name, today=today)

    path = '{stem}/original/{table}.csv'.format(stem=stem,
                                                     table=table_name)

    # Check if a directory with the same name already exists in the
    # S3 bucket, and if so change the key.
    unique_path = check_duplicates(path)

    # Write the file to Amazon S3 and delete the temporary file
    copy_source = BUCKET_NAME + '/' + tmp_path
    s3.Object(BUCKET_NAME, unique_path).copy_from(CopySource=copy_source)
    s3.Object(BUCKET_NAME, tmp_path).delete()

    # Generate a README file
    # readme_template = open(os.path.join(settings.BASE_DIR,
    #    config, 'readme_template'), 'r').read()

    # readme = readme_template.format(topic=topic.upper(),
    #    div='=' * len(topic),
    #    reporter=reporter_name,
    #    aq=next_aquisition,
    #    owner=owner,
    #    contact=press_contact,
    #    number=press_contact_number,
    #    email=press_contact_email)
    #
    # Write the README to the S3 bucket
    # bucket.put_object(Key='{stem}/README.txt'.format(unique_stem),
    # Body=readme)

    return unique_path


def write_tempfile_to_s3(local_path, table_name):
    """
    Write a temporary file to the S3 server. Use it later to execute LOAD DATA
    INFILE
    """
    s3 = start_s3_session()
    bucket = s3.Bucket(BUCKET_NAME)

    s3_path = check_duplicates('tmp/{}.csv'.format(table_name))

    bucket.upload_file(local_path, s3_path)

    return s3_path
