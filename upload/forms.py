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

        databases = [[None, 'None selected']]
        for db in data:
            pair = list(db)
            pair.extend(list(db))
            databases.append(pair)

        self.fields['db_select'] = forms.ChoiceField(label='Select a database',
            choices=databases,
            initial=None,
            required=False)

        # Set Bootstrap classes on form inputs
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    # Customize the clean method to check that one and only one of the two DB 
    # inputs contains valid data
    def clean(self):
        cleaned_data = super(DataForm, self).clean()
        select = cleaned_data.get('db_select')
        if not cleaned_data.get('db_input') and not cleaned_data.get('db_select'):
            raise forms.ValidationError(
                'Please select a database or input a new database name'
            )

    # Prevent SQL injection by escaping any data that will be passed as 
    # parameters to the raw SQL query
    def clean_db_input(self):
        data = self.cleaned_data['db_input']
        r = re.compile(r'\W')
        if r.search(data) != None:
            raise forms.ValidationError(
                'Only alphanumeric characters and underscores (_) are allowed in the database name'
            )
        return data


    data_file = forms.FileField(label='File')
    table_name = forms.SlugField(label='Table name', max_length=100)
    db_input = forms.CharField(label='Create a new database', max_length=100, required=False)
    #delimiter = forms.ChoiceField(label='Delimiter', choices=DELIMITERS, initial=',')
    source = forms.CharField(label='Source', max_length=100, required=False)
    topic = forms.CharField(label='Topic', max_length=100, required=False)
    next_aquisition = forms.DateField(label='When to update data', widget=forms.SelectDateWidget, required=False)
    press_contact = forms.CharField(label='Press contact name', max_length=100, required=False)
    press_contact_number = forms.CharField(label='Press contact number', max_length=100, required=False)
    press_contact_email = forms.EmailField(label='Press contact email', required=False)

