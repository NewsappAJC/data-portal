# Standard library imports
import os

# Django imports
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

# Third-party imports
import sqlalchemy
from celery.result import AsyncResult
from redis.exceptions import ConnectionError

# Local imports
from .forms import MetadataForm, FileForm
from .models import Column, Table, Contact
from .utils import S3Manager, TableFormatter, Index
from search.utils import SearchManager
# Have to do an absolute import below because of how celery resolves paths :(
from upload.tasks import load_infile

# Constants
BUCKET_NAME = os.environ.get('S3_BUCKET')
URL = os.environ.get('DATA_WAREHOUSE_URL')

@login_required
def upload(request):
    # Get a list of most recent uploads for display in the sidebar
    uploads = Table.objects.order_by('-upload_time')[:5]
    context = {'meta_form': MetadataForm(), 'file_form': FileForm(), 'uploads': uploads}

    return render(request, 'upload/upload.html', context)

@login_required
def upload_file(request):
    form = FileForm(None, request.FILES)
    if request.method == 'POST':
        if form.is_valid():
            input_file = request.FILES['data_file']
            local_path = '/tmp/ajcMa-data-upload.csv'
            with open(local_path, 'wb+') as f:
                # Use chunks so as not to overflow system memory
                for i, chunk in enumerate(input_file.chunks()):
                    if (i == 0):
                        # TODO: should also handle splitting on \r\n like Windows
                        first_row = chunk.split('\n')[0]
                    f.write(chunk)

            request.session['local_path']= local_path

            return JsonResponse(
                {'headers': first_row.split(',')},
                status=200
            )

        else:
            # Setting safe to False is necessary to allow non-dict objects to
            # be serialized. To prevent XSS attacks make sure to escape the
            # text on the client side (the app does this). See django docs for
            # details about serializing non-dict objects
            return JsonResponse(
                form.errors.as_json(escape_html=True),
                status=400,
                safe=False
            )

@login_required
def add_metadata(request):
    """
    Write metadata about a file upload to session storage so that we can
    access it later when we upload to the Django DB
    """
    # Get form data, assign default values in case it's missing information.
    form = MetadataForm(request.POST)

    if request.method == 'POST':
        if form.is_valid():
            # Write the table to a temporary file in S3 that we can retrieve
            # later
            table_name = form.cleaned_data['table_name']
            local_path = request.session.get('local_path')
            s3 = S3Manager(local_path, table_name, BUCKET_NAME)
            request.session['s3_path'] = s3.write_file()

            request.session['table_params'] = {
                'topic': form.cleaned_data['topic'],
                'source': form.cleaned_data['source'],
                'next_update': form.cleaned_data['next_update'],
                'press_contact': form.cleaned_data['press_contact'],
                'press_contact_number': form.cleaned_data['press_contact_number'],
                'press_contact_email': form.cleaned_data['press_contact_email'],
                'press_contact_type': form.cleaned_data['press_contact_type'],
                'table_name': table_name
            }

            # Sanitize the column headers
            formatter = TableFormatter(local_path)
            request.session['headers'] = formatter.get_column_names()

            # Return an empty HTTP Response to the AJAX request to let it know
            # the request was successful. When the page receives a success
            # header it will automatically redirect to the next page
            return HttpResponse(status=200)

        else:
            return JsonResponse(
                form.errors.as_json(escape_html=True),
                status=400,
                safe=False
            )

    # If request method isn't POST then render the homepage
    return render(request,
                  'upload/file-select.html',
                  {'form': form})

@login_required
def table_detail(request, id):
    context = {}
    table = Table.objects.get(pk=id)
    context['table'] = table

    # Get column names and sample data to generate a table
    searchManager = SearchManager()
    select_query = 'SELECT * FROM imports.{} LIMIT 5;'.format(table.table)
    data = searchManager.simple_query(select_query)
    keys = data.keys()
    sample_rows = data.fetchall()
    context['preview'] = {'headers': keys, 'data': sample_rows}

    # Get the number of rows in the table
    n = searchManager.simple_query('SELECT COUNT(*) FROM imports.{}'.format(table.table))
    context['num_rows'] = n.first()[0]

    return render(request, 'upload/detail.html', context)

@login_required
def categorize(request):
    """
    Prompt the user to select categories for each column in the data.
    """
    context = {
        'headers': request.session['headers'],
        'ajc_categories': Column.INFORMATION_TYPE_CHOICES,
        'datatypes': Column.MYSQL_TYPE_CHOICES,
        'range': range(3)
    }

    return render(request, 'upload/categorize.html', context)


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
        # for a dynamically generated form. We force the user to select a
        # category for every header, so if any of the headers don't have a 
        # category selected, display an error message
        headers = request.session['headers']

        if len(keys) < len(headers):
            messages.add_message(request, messages.ERROR,
                                 'Please select a category for every column')
            return redirect(reverse('upload:categorize'))


        table_params = request.session['table_params']
        table_params['columns'] = headers
        table_params['s3_path'] = request.session['s3_path']

        # Launch an asynchronous task for the potentially time-intensive job
        # of executing the LOAD DATA INFILE statement
        try:
            task = load_infile.delay(**table_params)
        # TODO : should also handle the ValueError for failing to connect to S3
        except ConnectionError:
            message = 'Unable to connect to the Redis server'
            messages.add_message(request, messages.ERROR, message)
            return redirect(reverse('upload:index'))

        # We will use the id to poll Redis for task status in the
        # check_task_status view
        request.session['task_id'] = task.id

        # Get the index of each column header and set the appropriate category
        # Because the form data is POSTed as a dict we can't be sure about
        # the order
        for key in keys:
            for i, val in enumerate(headers):
                if val['name'] == key:
                    header_index = i
                    break

            val = request.POST[key]
            request.session['headers'][header_index]['category'] = val

        context = {'table': request.session['table_params']['table_name']}
        return render(request, 'upload/upload.html', context)

    return redirect(reverse('upload:index'))


@login_required
def check_task_status(request):
    """
    Polls the server to check the completion status of celery task. Performs
    one of the following:
    
    Update task progress

    If the task succeeded, return a sample of the data, and write metadata
    about the table and columns to Django DB.

    If the task failed, return error message.
    """
    # Use the ID of the async task saved in session storage to check the task
    # status
    p_id = request.session['task_id']
    response = AsyncResult(p_id)

    data = {
        'status': response.status,
        'result': response.result
    }

    # If the task is successful, write information about the upload to the
    # Django DB.
    if data['status'] == 'SUCCESS' and not data['result']['error']:
        # Create a new table record in the Django DB
        params = request.session['table_params']
        t = Table(
            table=data['result']['table'],
            topic=params['topic'],
            user=request.user,
            source=params['source'],
            upload_log=data['result']['warnings'],
            path=data['result']['final_s3_path'],
            next_update=params['next_update']
        )
        t.save()

        # Create a new column record in the Django DB for each column in
        # the table
        c = Contact(
            table=t,
            name=params['press_contact'],
            email=params['press_contact_email'],
            phone=params['press_contact_number'],
            contact_type=params['press_contact_type']
        )
        c.save()

        engine = sqlalchemy.create_engine(URL)
        connection = engine.connect()
        index = Index(table_id=t.id, connection=connection)

        # Create column objects for each column in the table, and create an
        # index for the ones we're interested in
        for i, session_header in enumerate(request.session['headers']):
            task_header = data['result']['headers'][i]
            c = Column(table=t,
                       column=session_header['name'],
                       mysql_type=task_header['datatype'],
                       information_type=session_header['category'],
                       column_size=task_header['length'])
            c.save()
            # Need to fix this so that it's stored as None
            if c.information_type != 'None':
                index.create_index(c.information_type)


    # If response isn't JSON serializable then it's an error message.
    # Convert it to a string and return it
    try:
        return JsonResponse(data)
    except TypeError:
        data['result'] = str(data['result'])
        return JsonResponse(data)

def logout_user(request):
    """
    Use django's default logout function to log the user out
    """
    logout(request)
    messages.add_message(request, messages.ERROR, 'You have been logged out')
    return redirect(reverse('upload:login'))
