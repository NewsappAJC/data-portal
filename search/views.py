# Stdlib imports
import os

# Django imports
from django.shortcuts import render

# Third-party imports
from sqlalchemy import create_engine

# Local imports
from .utils import warehouse_search

def search(request):
    if request.method = 'POST':
        query = request.POST.get('name_query', None)

        # Connect to the MySQL DB
        engine = create_engine(os.environ.get('DATA_WAREHOUSE_URL'))
        connection = engine.connect()




