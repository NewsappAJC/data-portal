# Stdlib imports
import os
import csv
import re

# Django imports
from django.utils.html import escape
from django.shortcuts import render
from django.http import HttpResponse

# Local module imports
from .utils import SearchManager

BUCKET_NAME = os.environ.get('S3_BUCKET')
TMP_PATH = os.path.join('/tmp', 'ajc-import-searchfile.csv')

def search(request):
    results = []
    context = {'results': results, 'detail': False}

    if request.method == 'POST':
        query = request.POST.get('query', None)
        filters = request.POST.get('filter', None)

        filter_names = {
            'add': 'address',
            'name': 'name'
        }

        try:
            filters = filters.split() # If only one is selected it'll be a string
        except AttributeError:
            pass

        if not query:
            context['error'] = 'Please enter a search term'

        else:
            context['query'] = escape(query)
            context['filter'] = filter_names[filters[0]]

            searchManager = SearchManager()
            res = searchManager.warehouse_search(query, filters)

            if not res:
                context['error'] = '''No results found for "{}".'''.format(query)
            else:
                context['results'] = res

    return render(request, 'search/search.html', context)


def get_all_results(request):
    sql_query = request.session.get('sql_search_query')

    searchManager = SearchManager()
    search_result = searchManager.simple_query(sql_query)

    # Add error handling here for cases where the search results array is empty
    with open(TMP_PATH, 'wb') as f:
        # fields = search_result[0].keys()
        writer = csv.writer(f, delimiter=',')
        writer.writerows([row.values() for row in search_result])

    # Generate an HttpResponse that prompts the user to download the CSV
    response = HttpResponse(file(TMP_PATH), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=ajc-search-results.csv'
    return response

def search_detail(request):
    results = []

    if request.method == 'POST':
        query = request.POST.get('query', None)
        table = request.POST.get('table', None)
        search_columns = request.POST.get('search_columns', None)

        # Return a maximum of 50 rows and create a link to download a CSV
        # with all the search results
        searchManager = SearchManager()
        params = {'query': query, 'table': table,
                  'search_columns': search_columns, 'preview': 50}
        sql_query, search_result = searchManager.table_search(**params)
        results.append(search_result)

        # Strip the LIMIT clause out of the SQL query and save it to session
        # storage
        r = re.compile(r'LIMIT \d+$')
        sql_query = r.sub('', sql_query)
        request.session['sql_search_query'] = sql_query

        context = {'query': query, 'result': results[0], 'detail': True}

    else:
        context = {'results': []}

    return render(request,'search/detail.html', context)

