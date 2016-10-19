from django.conf.urls import url
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^search/', views.search)
#    url(r'^results/$', views.results)
]