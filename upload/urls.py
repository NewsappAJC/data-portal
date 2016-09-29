from django.conf.urls import url
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='upload.html')),
    url(r'^upload-file/$', views.upload_file),
]
