from django.conf.urls import url
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^$', views.upload_file),
    url(r'^login/$', auth_views.login)
]
