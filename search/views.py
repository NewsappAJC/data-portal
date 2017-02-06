# Stdlib imports
from __future__ import unicode_literals
import os

# Django imports
from django.utils.html import escape
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings

# Third-party imports
import boto3
import botocore

# Local module imports
#from .forms import DataForm
from .utils import warehouse_search, table_search
from upload.models import Table

BUCKET_NAME = os.environ.get('S3_BUCKET')

def search(request):
    results = []
    context = {'results': results, 'detail': False}

    if request.method == 'POST':
        query = request.POST.get('query', None)
        if not query:
            context['error'] = 'Please enter a search term'

        else:
            context['query'] = escape(query)
            res = warehouse_search(query)
            if not res:
                context['error'] = '''No results found for "{}".'''.format(query)
            else:
                context['results'] = res

    import pdb
    pdb.set_trace()
    return render(request, 'search/search.html', context)


def get_presigned_url(request, id):
    table = Table.objects.get(id=id)
    if not table.path:
        return JsonResponse(status=400, safe=False)

    path = table.path
    try:
        client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY,
                              aws_secret_access_key=settings.AWS_SECRET_KEY)
    except botocore.exceptions.ClientError as e:
        return JsonResponse(str(e))

    p = {'Bucket': BUCKET_NAME, 'Key': path}
    url = client.generate_presigned_url(ClientMethod='get_object', Params=p)

    return JsonResponse(url)

def show_full_dataset(request):
    results = []

    if request.method == 'POST':
        query = request.POST.get('query', None)
        table = request.POST.get('table', None)
        search_columns = request.POST.get('search_columns', None)
        preview = False

        results.append(table_search(query, table, search_columns, preview))
        context = {'query': query, 'results': results, 'detail': True}

    else:
        context = {'results': []}

    return render(request,'search/search.html', context)

