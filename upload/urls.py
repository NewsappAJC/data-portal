from django.conf.urls import url
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^$', views.upload_file),
    url(r'^check-casting/$', views.check_casting, name='check-casting')
]
