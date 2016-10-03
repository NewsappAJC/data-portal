# Python standard library imports
import os
import time
import subprocess

# Django imports
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.db import OperationalError
from django.conf import settings

# Third-party imports
import boto3, botocore
import csvkit
import MySQLdb
from sqlalchemy.engine.url import make_url

# Local imports
from .forms import DataForm

# Constants
# Get database details from environmental variables
BUCKET_NAME = os.environ.get('S3_BUCKET')

#------------------------------------#
# Take file uploaded by user, use
# csvkit to generate a DB schema, and write
# to an SQL table. Copy file and related 
# information to S3 bucket.
#------------------------------------#
# TODO accept more than one file

def upload_file(request):
    form = DataForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            # Assign form values to variables
            fcontent = form.cleaned_data['file'].read()
            db_name = settings.DATABASES['default']['NAME']
            table_name = form.cleaned_data['table_name']
            topic = form.cleaned_data['topic']
            reporter_name = form.cleaned_data['reporter_name']
            next_aquisition = form.cleaned_data['next_aquisition']
            owner = form.cleaned_data['owner']
            press_contact = form.cleaned_data['press_contact']
            press_contact_number = form.cleaned_data['press_contact_number']
            press_contact_email =  form.cleaned_data['press_contact_email']

            # Access bucket using credentials in ~/.aws/credentials
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(BUCKET_NAME)

            # Check if a file with the same name already exists in the
            # S3 bucket, and if so throw an error and return to the index
            # page
            try:
                bucket.download_file(table_name, '/tmp/s3_test_file')
                messages.add_message(request, messages.ERROR, 'A file with that name already exists')
                return render(request, 'upload.html', {'form': form})
            except botocore.exceptions.ClientError:
                pass

            # Write the file to the /tmp/ directory, then use
            # csvkit to generate the CREATE TABLE query
            path = '/tmp/' + table_name + '.csv'
            with open(path, 'w') as f:
                f.write(fcontent)

            try:
                db_url = make_url(os.environ['DATABASE_URL'])
            except KeyError:
                raise KeyError('Set the DATABASE_URL environmental variable')

            # Run a LOAD DATA INFILE query to create a table in the data warehouse
            with connection.cursor() as cursor: 
                create_table_q = subprocess.check_output(['csvsql', path])
                query = r"""
                    {create_table}
                    LOAD DATA LOCAL INFILE "{path}" INTO TABLE {name}
                    FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
                    IGNORE 1 LINES;
                    """.format(create_table=create_table_q, path=path, name=table_name)
                try:
                    cursor.execute(query) # Create the table and load in the data
                except OperationalError: 
                    messages.add_message(request, messages.ERROR, 
                        'The database already contains a table named {}. Please try again.'.format(table_name))
                    return render(request, 'upload.html', {'form': form})

            # Return a preview of the top few rows in the table
            # and check if the casting is correct
            # After running the create table query, return a
            # log of the issues that need to be fixed if any

            # Write the file to Amazon S3
            # bucket.put_object(Key=fkey, Body=fcontent)
    return render(request, 'upload.html', {'form': form})

