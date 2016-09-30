from django import forms

REPORTERS = (
    ('Jonathan Cox', 'Jonathan Cox'),
    ('Jeff Ernsthausen', 'Jeff Ernsthausen'),
    ('Emily Merwin', 'Emily Merwin'),
    ('Saurabh Datar', 'Saurabh Datar')
)

class DataForm(forms.Form):
    file = forms.FileField()
    table_name = forms.CharField(label='Dataset name (eg: ga_doc_incidents)', max_length=100)
    topic = forms.CharField(label='Topic', max_length=100)
    reporter_name = forms.ChoiceField(label='Reporter who got this data', choices=REPORTERS)
    next_aquisition = forms.DateField(label='When to update dataset', widget=forms.SelectDateWidget)
    owner = forms.CharField(label='Who supplied this dataset?', max_length=100)
    press_contact = forms.CharField(label='Press contact name', max_length=100)
    press_contact_number = forms.CharField(label='Press contact number', max_length=100)
    press_contact_email = forms.CharField(label='Press contact email', max_length=100)
