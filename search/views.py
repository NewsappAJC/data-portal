# Django imports
from django.shortcuts import render

# Local module imports
#from .forms import DataForm
from .utils import warehouse_search, table_search

def search(request):
    if request.method == 'POST':
        query = request.POST.get('query', None)

        results = warehouse_search(query)

        return render(request, 'search-results.html', {'results': results, 'query': query})

    else:
        return render(request, 'search.html')


def show_full_dataset(request):
    if request.method == 'POST':
        query = request.POST.get('query', None)
        table = request.POST.get('table', None)
        search_columns = request.POST.get('search_columns', None)
        preview = False

        results = []
        results.append(table_search(query, table, search_columns, preview))

        return render(request,'search/search-results.html', {'results': results})

    else:
        return render(request, 'search/search.html')

