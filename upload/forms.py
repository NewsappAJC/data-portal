# Standard library imports
import re
import os

# Third party imports
from django import forms
import sqlalchemy

# Local imports
from .models import Contact

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

# 10MB = 10485760
MAX_UPLOAD_SIZE = 10485760 * 2


class DataForm(forms.Form):
    # Initialize the data upload form with a list of databases on the MySQL
    # server
    def __init__(self, *args, **kwargs):
        super(DataForm, self).__init__(*args, **kwargs)

        # Set Bootstrap classes on form inputs
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

    # Internal method that checks for non-alphanumeric characters and raises an
    # error if it encounters any
    def _sanitize(self, data):
        r = re.compile(r'\W')
        if r.search(data) is not None:
            raise forms.ValidationError(
                'Only alphanumeric characters and underscores (_) are allowed.'
            )
        return data

    # Ensure that the file isn't >20MB.
    def clean_data_file(self):
        data = self.cleaned_data['data_file']
        if data._size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                'Sorry, we can\'t handle files bigger than 10MB yet.'
            )
        if not data.name.endswith('.csv'):
            raise forms.ValidationError(
                'Please select a .csv file'
            )
        return data

    def clean_table_name(self):
        input_name = self.cleaned_data['table_name']

        engine = sqlalchemy.create_engine(os.environ.get('DATA_WAREHOUSE_URL'))
        connection = engine.connect()
        names = [n[0] for n in connection.execute('SHOW TABLES IN imports;')]
        if input_name in names:
            raise forms.ValidationError(
                'A table with that name already exists in the database.'
            )

        connection.close()

        data = self._sanitize(self.cleaned_data['table_name'])
        return data

    data_file = forms.FileField(label='File')
    table_name = forms.CharField(label='Table name', max_length=100,
                                 widget=forms.TextInput(attrs={'placeholder': 'Table name'}))
    source = forms.CharField(label='Source', max_length=100, required=True,
                             widget=forms.TextInput(attrs={'placeholder': 'Source'}))
    topic = forms.CharField(label='Topic', max_length=100, required=True,
                            widget=forms.TextInput(attrs={'placeholder': 'Topic'}))
    next_update = forms.DateField(label='When to update data',
                                  widget=forms.SelectDateWidget,
                                  required=False,
                                  input_formats=['%m/%d/%Y'])
    press_contact = forms.CharField(label='Name',
                                    max_length=100,
                                    required=False, widget=forms.TextInput(attrs={'placeholder': 'Press contact name'}))
    press_contact_number = forms.CharField(label='Press contact number',
                                           max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone number'}))
    press_contact_email = forms.EmailField(label='Press contact email',
                                           required=False, widget=forms.TextInput(attrs={'placeholder': 'Email'}))
    press_contact_type = forms.ChoiceField(label='Type',
                                           choices=Contact.CONTACT_TYPE_CHOICES,
                                           required=True)
