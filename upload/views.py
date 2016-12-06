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
from .utils import get_column_names, write_tempfile_to_s3
# Have to do an absolute import here because of how celery resolves paths. See
# http://docs.celeryproject.org/en/latest/userguide/tasks.html#task-naming-relative-imports
from upload.tasks import load_infile


@login_required
def upload_file(request):
    """
    Take file uploaded by user, use csvkit to generate a DB schema, and write 
    to an SQL table. Copy file and metadata to s3.
    """
    # Get form data, assign default values in case it's missing information.
    form = DataForm(request.POST or None, request.FILES or None)

    # Get a list of most recent uploads to display in the sidebar
    uploads = Table.objects.order_by('-upload_time')[:5]

    if request.method == 'POST':
        if form.is_valid():
            inputf = request.FILES['data_file']
            table_name = form.cleaned_data['table_name']
            # Write the file to a path in the /tmp directory for upload to S3
            path = '/tmp/{}.csv'.format(table_name)
            with open(path, 'wb+') as f:
                # Use chunks so as not to overflow system memory
                for chunk in inputf.chunks():
                    f.write(chunk)

            # Store the table config in session storage so that other views can
            # access it later.
            db_name = form.cleaned_data['db_input'] or form.cleaned_data['db_select']
            request.session['table_params'] = {
                'topic': form.cleaned_data['topic'],
                'db_name': db_name,
                'source': form.cleaned_data['source'],
                'table_name': table_name,
            }

            # Write the CSV to a temporary file in the Amazon S3 bucket that 
            # we will retrieve later before uploading to the MySQL server
            request.session['s3_path'] = write_tempfile_to_s3(path, table_name)

            headers = get_column_names(path)
            request.session['headers'] = headers

            # Return an empty HTTP Response to the AJAX request to let it know
            # the request was successful.
            return HttpResponse(status=200)

        else:
            # Setting safe to False is necessary to allow non-dict objects to be serialized.
            # To prevent XSS attacks make sure to escape the results on client side.
            # See https://docs.djangoproject.com/en/1.10/ref/forms/api/#django.forms.Form.errors.as_json
            # More about serializing non-dict objects: https://docs.djangoproject.com/en/1.10/ref/request-response/#serializing-non-dictionary-objects
            return JsonResponse(
                form.errors.as_json(escape_html=True),
                status=400,
                safe=False
            )

    # If request method isn't POST or if the form data is invalid render the
    # homepage
    return render(request, 'upload/file-select.html', {'form': form, 'uploads': uploads})

@login_required
def categorize(request):
    """
    Prompt the user to select categories for each column in the data, then
    begin upload task
    """
    context = {
        'headers': request.session['headers'],
        'ajc_categories': Column.INFORMATION_TYPE_CHOICES,
        'datatypes': Column.MYSQL_TYPE_CHOICES
    }

    return render(request, 'upload/categorize.html', context)


@login_required
def check_task_status(request):
    """
    Poll to check the completion status of celery task. If task has succeeded,
    return a sample of the data, and write metadata about upload to Django DB.
    If failed, return error message.
    """
    p_id = request.session['task_id']
    response = AsyncResult(p_id)
    data = {
        'status': response.status,
        'result': response.result
    }

    # If the task is successful, write information about the upload to the Django 
    # DB. Find a way to make sure this database reflects changes to the 
    if data['status'] == 'SUCCESS' and not data['result']['error']:
        # Create a table object in the Django DB
        params = request.session['table_params']
        t = Table(
            table=data['result']['table'],
            url=data['result']['url'],
            database=params['db'],
            topic=params['topic'],
            user=request.user,
            source=params['source'],
            upload_log=data['result']['warnings']
        )
        t.save()

        # Create column objects for each column in the table
        # Some of the data about each column is held in session storage,
        # some is returned by the task. Both store the columns in the same order.
        session_headers = request.session['headers']
        for i, header in enumerate(data['result']['headers']):
            c = Column(table=t, 
                column=session_headers[i]['name'],
                mysql_type=header['datatype'],
                information_type=session_headers[i]['category'],
                column_size=header['length']
            )
            c.save()

    # If response isn't JSON serializable it's an error message. Convert it to
    # a string and return that instead
    try:
        return JsonResponse(data)
    except TypeError:
        data['result'] = str(data['result'])
        return JsonResponse(data)

@login_required
def write_to_db(request):
    """
    Download a file from S3 to the /tmp directory, then execute a LOAD
    DATA INFILE statement to push it to the MySQL server
    """
    if request.method == 'POST':
        # We don't want to create a column for the csrf token so strip it out
        keys = [x for x in request.POST if x != 'csrfmiddlewaretoken']
        # Have to validate manually because we can't use a Django form class 
        # for a dynamically generated form. We force user to select a category 
        # for every header
        if len(keys) < len(request.session['headers']):
            messages.add_message(request, messages.ERROR, 'Please select a category for every column')
            return redirect('/categorize/')

        params = request.session['table_params']
        cparams = {key: value for key, value in params.items()}
        cparams['columns'] = request.session['headers']
        cparams['s3_path'] = request.session['s3_path']

        # Begin load data infile query as a separate task so it doesn't slow response
        # load_infile accepts the following arguments:
        # (s3_path, db_name, table_name, columns)
        task = load_infile.delay(**cparams)

        # We will use the id to poll Redis for task status in the
        # check_task_status view
        request.session['task_id'] = task.id
        request.session['task_type'] = 'final'

        headers = request.session['headers']

        # Get the index of each column header and set the appropriate category
        for key in keys:
            hindex = [i for i, val in enumerate(headers) if headers[i]['name'] == key][0]
            headers[hindex]['category'] = request.POST[key]

        return render(request, 'upload/upload.html', {'table': request.session['table_params']['table_name']})

    return redirect('/')

def logout_user(request):
    """
    Log a user out
    """
    logout(request)
    messages.add_message(request, messages.ERROR, 'You have been logged out')
    return redirect('/login/')
