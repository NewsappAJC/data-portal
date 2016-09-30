# Python standard library imports
import subprocess

# Django imports
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.template import RequestContext
from django.db import connection

# Third-party imports
import mysqlclient
import boto3, botocore
import csvkit

# Get database details from environmental variables
BUCKET_NAME = os.environ.get('S3_BUCKET')

def upload_file(request):
    if request.method == 'POST':
        fcontent = request.FILES['file-input'].read()
        fkey = request.FILES['file-input'].name

        # Access bucket using credentials in ~/.aws/credentials
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(BUCKET_NAME)

        # Check if a file with the same name already exists in the
        # S3 bucket, and if so throw an error and return to the index
        # page
        try:
            bucket.download_file(fkey, '/tmp/boto_test')
            messages.add_message(request, messages.ERROR, 'A file with that name already exists')
            return HttpResponseRedirect('/')
        except botocore.exceptions.ClientError:
            pass

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
                LOAD DATA INFILE {path} INTO TABLE {name}
                FIELDS TERMINATED BY "," LINES TERMINATED BY "\r\n"
                IGNORE 1 LINES;
                """.format(create_table=create_table_query, path=path, name=fkey[:-4])
            cursor.execute(query) # Create the table and load in the data

        # Return a preview of the top few rows in the table
        # and check if the casting is correct
        # After running the create table query, return a
        # log of the issues that need to be fixed if any

        # Write the file to Amazon S3
        bucket.put_object(Key=fkey, Body=fcontent)
        return HttpResponse('File uploaded to S3.<br> Query: ' + query)
