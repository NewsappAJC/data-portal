from django import forms

class SearchForm(forms.Form):
    name_query = forms.CharField(label='Search for a name', max_length=100, initial='Matthews')