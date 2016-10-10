# Python standard lib imports
import json
import os
import time
import subprocess
import logging

# Django imports
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import logout
from django.conf import settings

# Third-party imports
import boto3, botocore
from celery.result import AsyncResult

# Local imports
from .forms import DataForm
# Have to do an absolute import here for celery. See
# http://docs.celeryproject.org/en/latest/userguide/tasks.html#task-naming-relative-imports
from upload.tasks import load_infile


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

            # Load data infile doesn't work on files in memory, so write the file to the /tmp/ directory
            path = '/tmp/' + table_name + '.csv'
            with open(path, 'w') as f:
                f.write(fcontent)

            # Begin load data infile query as a separate task so it doesn't slow response
            # Add the id of the process to the session so we can poll it and check if it's 
            # successful
            x = load_infile.delay(path, db_name, table_name, delimiter)
            request.session['id'] = x.id

            return redirect('/results/')

    return render(request, 'upload.html', {'form': form})

#------------------------------------#
# Poll to check the completion status of celery 
# task. If task is succeeded, return a sample of the
# data. If failed, return error message
#------------------------------------#
def check_task_status(request):
    p_id = request.session['id']
    response = AsyncResult(p_id)
    data = {
        'status': response.status, 
        'result': response.result
    }
    serialized = json.dumps(data)
    return HttpResponse(serialized)

#------------------------------------#
# Log a user out
#------------------------------------#
def logout_user(request):
    logout(request)
    messages.add_message(request, messages.ERROR, 'You have been logged out')
    return redirect('/login/')
