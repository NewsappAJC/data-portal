from django.shortcuts import render
#from .forms import DataForm
from .utils import warehouse_search

from sqlalchemy import create_engine
import os

engine = create_engine(os.environ['DATA_WAREHOUSE_URL'])
connection = engine.connect()

def search(request):
    if request.method == 'POST':
        query = request.POST.get('name_query', None)
            
        results = warehouse_search(query,connection)
            
        return render(request, 'search-results.html', {'results': results})
        
    else:
        return render(request, 'search.html')