from django.conf.urls import url
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^$', views.upload_file),
    url(r'^categorize/$', views.categorize),
    url(r'^upload/$', views.upload),
    url(r'^check-task-status/$', views.check_task_status),
    url(r'^login/$', auth_views.login),
    url(r'^logout/$', views.logout_user)
]
