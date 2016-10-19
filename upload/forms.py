from django import forms

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
    data_file = forms.FileField(label='File')
    delimiter = forms.ChoiceField(label='Delimiter', choices=DELIMITERS, initial=',')
    db_name = forms.CharField(label='Database name', max_length=100, initial='user_cox')
    table_name = forms.CharField(label='Table name', max_length=100, initial='test')
    topic = forms.CharField(label='Topic', max_length=100, initial='test')
    reporter_name = forms.ChoiceField(label='Reporter who aquired data', choices=REPORTERS, initial='Jonathan Cox')
    next_aquisition = forms.DateField(label='When to update data', widget=forms.SelectDateWidget, required=False)
    owner = forms.CharField(label='Source (Person or org)', max_length=100, initial='God')
    press_contact = forms.CharField(label='Press contact name', max_length=100, required=False)
    press_contact_number = forms.CharField(label='Press contact number', max_length=100, required=False)
    press_contact_email = forms.EmailField(label='Press contact email', required=False)

