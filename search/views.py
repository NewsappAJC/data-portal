# Stdlib imports
import os

# Django imports
from django.utils.html import escape
from django.shortcuts import render
from django.http import JsonResponse

# Local module imports
#from .forms import DataForm
from .utils import warehouse_search, table_search, get_url

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

    return render(request, 'search/search.html', context)


def get_presigned_url(request):
    query = request.session.get('sql_query')
    data_url = get_url(query)
    return JsonResponse(data_url)

def search_detail(request):
    results = []

    if request.method == 'POST':
        query = request.POST.get('query', None)
        table = request.POST.get('table', None)
        search_columns = request.POST.get('search_columns', None)
        preview = False

        # Return a maximum of 50 rows and create a link to download a CSV
        # with all the search results
        sql_query, search_results = table_search(query, table, search_columns, preview)
        results.append(search_results)
        # Save the SELECT query to get the full search results to session storage
        request.session['sql_search_query'] = sql_query

        context = {'query': query, 'result': results[0], 'detail': True}

    else:
        context = {'results': []}

    return render(request,'search/detail.html', context)

