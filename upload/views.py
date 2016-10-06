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
from django.contrib.auth import logout
from django.conf import settings

# Third-party imports
import boto3, botocore
import csvkit
import sqlalchemy
from sqlalchemy.engine.url import make_url # Used to parse database information from env variable

# Local imports
from .forms import DataForm

# Set constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ['DATA_WAREHOUSE_URL']

#------------------------------------#
# Take file uploaded by user, use
# csvkit to generate a DB schema, and write
# to an SQL table. Copy file and related 
# information to S3 bucket.
#------------------------------------#
# TODO accept more than one file
def upload_file(request):
    # Check that the user is authenticated. If not, redirect to the login page
    if not request.user.is_authenticated:
        return redirect('{}?next={}'.format(settings.LOGIN_URL, request.path))

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

            # Create a connection to the data warehouse 
            engine = sqlalchemy.create_engine(URL + '?local_infile=1')
            connection = engine.connect()

            # Check if a database with the given name exists. If it doesn't, create one.
            connection.execute('CREATE DATABASE IF NOT EXISTS {}'.format(db_name))
            connection.execute('USE {}'.format(db_name))
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
            connection.execute(query)

            # Return a preview of the top few rows in the table
            # to check if the casting is correct. Save data to session
            # so that it can be accessed by other views
            data = connection.execute('SELECT * FROM {}'.format(table_name))
            headers = data.keys()

            return render(request, 'check-casting.html', {'data': data,
                'headers': headers,
                'bucket': BUCKET_NAME,
                'db': db_name})

    return render(request, 'upload.html', {'form': form})

def logout_user(request):
    logout(request)
    messages.add_message(request, messages.ERROR, 'You have been logged out')
    return redirect('/login/')
