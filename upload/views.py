# Python standard lib imports
import os
import time
import subprocess
import logging
from datetime import date

# Django imports
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.conf import settings

# Third-party imports
import boto3, botocore
import csvkit
from sqlalchemy.engine.url import make_url # Used to parse database information from env variable
import MySQLdb

# Local imports
from .forms import DataForm

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = make_url(os.environ['DATABASE_URL'])

#------------------------------------#
# Take file uploaded by user, use
# csvkit to generate a DB schema, and write
# to an SQL table. Copy file and related 
# information to S3 bucket.
#------------------------------------#
# TODO accept more than one file
def upload_file(request):
    # Get form data, assign default values in case it's missing information.
    form = DataForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            # Assign form values to variables
            fcontent = form.cleaned_data['file'].read()

            delimiter = form.cleaned_data['delimiter']
            db_name = form.cleaned_data['db_name']
            table_name = form.cleaned_data['table_name']
            topic = form.cleaned_data['topic']
            reporter_name = form.cleaned_data['reporter_name']
            next_aquisition = form.cleaned_data['next_aquisition']
            owner = form.cleaned_data['owner']
            press_contact = form.cleaned_data['press_contact']
            press_contact_number = form.cleaned_data['press_contact_number']
            press_contact_email =  form.cleaned_data['press_contact_email']

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

            # Csvkit doesn't work on files in memory, so write the file to the /tmp/ directory
            path = '/tmp/' + table_name + '.csv'
            with open(path, 'w') as f:
                f.write(fcontent)
            print path

            # Try to get database parameters from the $DATABASE_URL environmental variable
            try:
                db_host = URL.host
                db_user = URL.username
                db_pw = URL.password
            except KeyError:
                raise KeyError('The DATABASE_URL environmental variable is not set')

            # Create a connection to the data warehouse 
            # TODO add a try-except here in case the DB connection fails
            connection = MySQLdb.connect(host=db_host, 
                user=db_user, 
                passwd=db_pw, 
                local_infile=True)
            cursor = connection.cursor()

            logging.info('Connected to MySQL server')

            # Check if a database with the given name exists. If it doesn't, create one.
            cursor.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
            connection.select_db(db_name)
            logging.info('Using database {}'.format(db_name))

            # Use csvkit to generate a CREATE TABLE statement based on the data types
            # in the csv
            create_table_q = subprocess.check_output(['csvsql', path])
            query = r"""
                {create_table}
                LOAD DATA LOCAL INFILE "{path}" INTO TABLE {db}.{table}
                FIELDS TERMINATED BY "{delimiter}" LINES TERMINATED BY "\n"
                IGNORE 1 LINES;
                """.format(create_table=create_table_q,
                        path=path,
                        db=db_name,
                        table=table_name,
                        delimiter=delimiter)

            # Create the table and load in the data
            try:
                cursor.execute(query)
                cursor.close() # Have to close cursor before you can commit
                connection.commit() # Have to commit to make LOAD INFILE work
            except connection.OperationalError: # TODO Ensure this error is actually occurring due to duplicate tables
                messages.add_message(request, messages.ERROR, 
                    '''The database already contains a table named {}. 
                    Please try again with a different name.'''.format(table_name))
                return render(request, 'upload.html', {'form': form})

            logging.info('Data loaded into SQL server')

            # Return a preview of the top few rows in the table
            # to check if the casting is correct. Save data to session
            # so that it can be accessed by other views
            cursor = connection.cursor() # Create a new cursor to query the table created
            cursor.execute('SELECT * FROM {}'.format(table_name))
            data = cursor.fetchall()

            dataf = [list(x) for x in data] # fetchall() returns a tuple, so convert to list for editing
            headers = [x[0] for x in cursor.description]

            # MySQLdb doesn't automatically garbage collect connections so close them here
            cursor.close()
            connection.close()

            return render(request, 'check-casting.html', {'data': dataf, 'headers': headers, 'bucket': BUCKET_NAME, 'db': db_name})

    return render(request, 'upload.html', {'form': form})

