from django.shortcuts import render

from .forms import MySearchForm

def match_list(request):
    if request.method == 'POST':
        form = MySearchForm(request.POST)
        if form.is_valid():
            search = form.cleaned_data['search']
            
            # Run ES search with search terms here. Maybe
            # hand off the job to a celery worker if necessary
            
            results = ES_dict

            return render(request, 'search.html', {'results': results})

