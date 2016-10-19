# Python standard lib imports
import json
import os
import logging
import time

# Django imports
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
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
            delimiter = form.cleaned_data['delimiter']
            db_name = form.cleaned_data['db_name']
            table_name = form.cleaned_data['table_name']
            path = '/tmp/{}.csv'.format(table_name)

            # Handle uploaded file in chunks so we don't overwhelm the system's memory
            with open(path, 'wb+') as f:
                for chunk in request.FILES['data_file'].chunks():
                    f.write(chunk)

            # Begin load data infile query as a separate task so it doesn't slow response
            # load_infile accepts args in the following order: (db_name, table_name, path, delimiter=',')
            task = load_infile.delay(db_name, table_name, path, delimiter)

            # Add the id of the process to the session so we can poll it and check if it's completed.
            request.session['id'] = task.id
            request.session['table'] = table_name

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
    return JsonResponse(data)

def results(request):
    return render(request, 'results.html', {'table': request.session['table']})

#------------------------------------#
# Log a user out
#------------------------------------#
def logout_user(request):
    logout(request)
    messages.add_message(request, messages.ERROR, 'You have been logged out')
    return redirect('/login/')
