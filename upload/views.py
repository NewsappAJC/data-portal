# Python standard library imports
import os
import time
import subprocess

# Django imports
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.template import RequestContext
from django.db import connection, OperationalError

# Third-party imports
import boto3, botocore
import csvkit

# Get database details from environmental variables
BUCKET_NAME = os.environ.get('S3_BUCKET')

def upload_file(request):
    if request.method == 'POST':
        fcontent = request.FILES['file-input'].read()
        fkey = request.FILES['file-input'].name

        # Write the file to the /tmp/ directory, then use
        # csvkit to generate the CREATE TABLE query
        path = '/tmp/' + fkey
        with open(path, 'w') as f:
            f.write(fcontent)

        # Run a LOAD DATA INFILE query to create a table in the data warehouse
        with connection.cursor() as cursor: 
            create_table_query = subprocess.check_output(['csvsql', path])
            query = r"""
                {create_table}
                LOAD DATA LOCAL INFILE "{path}" INTO TABLE {name}
                FIELDS TERMINATED BY "," LINES TERMINATED BY "\n"
                IGNORE 1 LINES;
                """.format(create_table=create_table_query, path=path, name=fkey[:-4])
            try:
                cursor.execute(query) # Create the table and load in the data
            except OperationalError: 
                messages.add_message(request, messages.ERROR, 
                    'The database already contains a table named {}. Please try again.'.format(fkey[:-4]))
                return HttpResponseRedirect('/')

        # Return a preview of the top few rows in the table
        # and check if the casting is correct
        # After running the create table query, return a
        # log of the issues that need to be fixed if any

        # Write the file to Amazon S3
        # bucket.put_object(Key=fkey, Body=fcontent)
        return HttpResponse('File uploaded to S3.<br>')

