# Python standard lib imports
import json
import os
import logging
import time
import pdb

# Django imports
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.conf import settings

# Third-party imports
import boto3, botocore
from celery.result import AsyncResult

# Local imports
from .forms import DataForm
from .models import Column, Table, Contact
from .utils import get_column_types, get_column_names
# Have to do an absolute import here for celery. See
# http://docs.celeryproject.org/en/latest/userguide/tasks.html#task-naming-relative-imports
from upload.tasks import load_infile, write_tempfile_to_s3


#------------------------------------#
# Take file uploaded by user, use
# csvkit to generate a DB schema, and write
# to an SQL table. Copy file and related 
# information to S3 bucket.
#------------------------------------#
# TODO accept more than one file
@login_required
def upload_file(request):
    # Get form data, assign default values in case it's missing information.
    form = DataForm(request.POST or None, request.FILES or None)

    # Get a list of most recent uploads to display in the sidebar
    uploads = Table.objects.order_by('-upload_time')[:5]

    if request.method == 'POST':
        if form.is_valid():
            table_name = form.cleaned_data['table_name']
            # Write the file to a path in the /tmp directory for manipulation later
            path = '/tmp/{}.csv'.format(table_name)

            with open(path, 'wb+') as f:
                # Handle uploaded file in chunks so we don't overwhelm the system's memory
                for i, chunk in enumerate(request.FILES['data_file'].chunks()):
                    # Write the first chunk to a sample file that we can use later to 
                    # infer datatype without reading the whole file into memory
                    f.write(chunk)

            # Store the table config in session storage so that other views can
            # access it.
            db_name = form.cleaned_data['db_input'] or form.cleaned_data['db_select']
            request.session['table_params'] = {
                'topic': form.cleaned_data['topic'],
                'db_name': db_name,
                'source': form.cleaned_data['source'],
                'table_name': table_name,
                'local_path': path
            }

            return redirect('/categorize/')

    # If request method isn't POST or if the form data is invalid
    return render(request, 'upload/file-select.html', {'form': form, 'uploads': uploads})

#------------------------------------#
# Prompt the user to select categories
# for each column in the data, then
# begin upload task
#------------------------------------#
@login_required
def categorize(request):
    # Infer column datatypes
    table_name = request.session['table_params']['table_name']
    local_path = request.session['table_params']['local_path']

    # Begin writing temp file to S3 so that we can access it later
    task = write_tempfile_to_s3.delay(local_path, table_name)
    request.session['task_id'] = task.id

    start_time = time.time()
    headers = get_column_names(local_path)
    request.session['headers'] = headers

    context = {
        'headers': headers,
        'ajc_categories': Column.INFORMATION_TYPE_CHOICES,
        'datatypes': Column.MYSQL_TYPE_CHOICES
    }

    return render(request, 'upload/categorize.html', context)


#----------------------------------------------------#
# Poll to check the completion status of celery 
# task. If task has succeeded, return a sample of the
# data, and write metadata about upload to Django DB. 
# If failed, return error message.
#----------------------------------------------------#
@login_required
def check_task_status(request):
    params = []
    p_id = request.session['task_id']
    response = AsyncResult(p_id)
    data = {
        'status': response.status,
        'result': response.result
    }

    # If the task is successful, write information about the upload to the Django DB
    #if data['status'] == 'SUCCESS' and not data['result']['error']:
    #    # Create a table object in the Django DB
    #    params = request.session['table_params']
    #    t = Table(
    #        table=params['table_name'],
    #        database=params['db_name'],
    #        topic=params['topic'],
    #        user=request.user,
    #        source=params['source'],
    #        upload_log=data['result']['warnings']
    #    )
    #    t.save()

    #    # Create column objects for each column in the table
    #    # Some of the data about each column is held in session storage,
    #    # some is returned by the task. Both store the columns in the same order.
    #    session_headers = request.session['headers']
    #    for i, header in enumerate(data['result']['headers']):
    #        c = Column(table=t, 
    #            column=session_headers[i]['name'],
    #            mysql_type=header['datatype'],
    #            information_type=session_headers[i]['category'],
    #            column_size=header['length']
    #        )
    #        c.save()

    try:
        return JsonResponse(data)
    # If response isn't JSON serializable it's an error message. Convert it to
    # a string and return that instead
    except TypeError:
        data['result'] = str(data['result'])
        return JsonResponse(data)

@login_required
def upload(request):
    # Begin load data infile query as a separate task so it doesn't slow response
    # load_infile accepts the following arguments:
    # (s3_path, db_name, table_name, columns)
    if request.method == 'POST':
        s3_path = request.POST.pop('tempfile')
        keys = [x for x in request.POST if x != 'csrfmiddlewaretoken']
        # Have to validate manually bc can't use a Django form class for a dynamically
        # generated form
        if len(keys) < len(request.session['headers']):
            messages.add_message(request, messages.ERROR, 'Please select a category for every column')
            return redirect('/categorize/')

        # Have to do this instead of using form class bc fields are dynamically generated
        params = request.session['table_params']
        fparams = {key: value for key, value in params.items()}
        fparams['columns'] = request.session['headers']
        fparams['s3_path'] = s3_path[0]

        task = load_infile.delay(**fparams)
        request.session['task_id'] = task.id # Use the id to poll Redis for task status
        headers = request.session['headers']

        # Probably needlessly complex logic to set the category for each columns
        for key in keys:
            hindex = [i for i, val in enumerate(headers) if headers[i]['name'] == key][0]
            headers[hindex]['category'] = request.POST[key]

        return render(request, 'upload/upload.html', {'table': request.session['table_params']['table_name']})

    return redirect('/')

#------------------------------------#
# Log a user out
#------------------------------------#
def logout_user(request):
    logout(request)
    messages.add_message(request, messages.ERROR, 'You have been logged out')
    return redirect('/login/')
