# Python standard lib imports
import os
import time
import subprocess
from datetime import date

# Django imports
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.db import OperationalError
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
            s3 = boto3.resource('s3')
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
            bucket.put_object(Key='{db_name}/{today}/original/{filename}'.format(
                db_name = db_name, 
                today = date.today().isoformat()
                filename = fkey), Body=fcontent)

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
            connection  = MySQLdb.connect(host=db_host, 
                user=db_user, 
                passwd=db_pw, 
                db=db_name,
                local_infile=True)
            cursor = connection.cursor()

            # Use csvkit to generate a CREATE TABLE statement based on the data types
            # in the csv
            create_table_q = subprocess.check_output(['csvsql', path])
            query = r"""
                {create_table}
                LOAD DATA LOCAL INFILE "{path}" INTO TABLE {name}
                FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
                IGNORE 1 LINES;
                """.format(create_table=create_table_q, path=path, name=table_name)

            # Create the table and load in the data
            try:
                cursor.execute(query)
                cursor.close()
                connection.commit() # Have to commit to make LOAD INFILE work
                connection.close()
            except OperationalError: # TODO Ensure this error is actually occurring due to duplicate tables
                messages.add_message(request, messages.ERROR, 
                    'The database already contains a table named {}. Please try again.'.format(table_name))
                return render(request, 'upload.html', {'form': form})
            

            # Return a preview of the top few rows in the table
            # and check if the casting is correct
            # After running the create table query, return a
            # log of the issues that need to be fixed if any

    return render(request, 'upload.html', {'form': form})

