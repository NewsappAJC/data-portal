# Standard library imports
import re
import os

# Third party imports
from django import forms
from django.forms import widgets

# Local module imports
import sqlalchemy
from sqlalchemy.engine.url import make_url

# Constants
URL = os.environ['DATA_WAREHOUSE_URL']

REPORTERS = (
    ('Jonathan Cox', 'Jonathan Cox'),
    ('Jeff Ernsthausen', 'Jeff Ernsthausen'),
    ('Emily Merwin', 'Emily Merwin'),
    ('Saurabh Datar', 'Saurabh Datar')
)

DELIMITERS = (
    (',', 'comma'),
    (';', 'semicolon')
)

class DataForm(forms.Form):
    # Initialize the data upload form with a list of databases on the MySQL server
    def __init__(self, *args, **kwargs):
        super(DataForm, self).__init__(*args, **kwargs)

        # Get database options
        engine = sqlalchemy.create_engine(URL)
        connection = engine.connect()
        data = connection.execute('SHOW DATABASES;')

        databases = []
        for db in data:
            pair = list(db)
            pair.extend(list(db))
            databases.append(pair)

        self.fields['db_name'] = forms.ChoiceField(label='Database', choices=databases, initial='user_cox')

        # Set classes on form inputs
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    data_file = forms.FileField(label='File')
    table_name = forms.SlugField(label='Table name', max_length=100)
    #delimiter = forms.ChoiceField(label='Delimiter', choices=DELIMITERS, initial=',')
    source = forms.CharField(label='Source', max_length=100, required=False)
    topic = forms.CharField(label='Topic', max_length=100, required=False)
    reporter_name = forms.ChoiceField(label='Reporter who aquired data', choices=REPORTERS)
    next_aquisition = forms.DateField(label='When to update data', widget=forms.SelectDateWidget, required=False)
    press_contact = forms.CharField(label='Press contact name', max_length=100, required=False)
    press_contact_number = forms.CharField(label='Press contact number', max_length=100, required=False)
    press_contact_email = forms.EmailField(label='Press contact email', required=False)

