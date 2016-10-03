from django import forms

REPORTERS = (
    ('Jonathan Cox', 'Jonathan Cox'),
    ('Jeff Ernsthausen', 'Jeff Ernsthausen'),
    ('Emily Merwin', 'Emily Merwin'),
    ('Saurabh Datar', 'Saurabh Datar')
)

class DataForm(forms.Form):
    file = forms.FileField()
    db_name = forms.CharField(label='Database name', max_length=100, initial='User_Jcox')
    table_name = forms.CharField(label='Table name', max_length=100, initial='asdf')
    topic = forms.CharField(label='Topic', max_length=100, initial='asdf')
    reporter_name = forms.ChoiceField(label='Reporter who aquired data', choices=REPORTERS, initial='Jonathan Cox')
    next_aquisition = forms.DateField(label='When to update data', widget=forms.SelectDateWidget, required=False)
    owner = forms.CharField(label='Dataset source', max_length=100, initial='asdf')
    press_contact = forms.CharField(label='Press contact name', max_length=100, initial='asdf')
    press_contact_number = forms.CharField(label='Press contact number', max_length=100, initial='asdf')
    press_contact_email = forms.CharField(label='Press contact email', max_length=100, initial='asdf')
