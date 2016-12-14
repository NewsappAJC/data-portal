from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

app_name = 'upload'
urlpatterns = [
    url(r'^$', views.upload_file, name='index'),
    url(r'^categorize/$', views.categorize, name='categorize'),
    url(r'^upload/$', views.write_to_db, name='write_to_db'),
    url(r'^check-task-status/$', views.check_task_status, name='check_status'),
    url(r'^get-presigned-url/$', views.get_presigned_url, name='get_presigned_url'),
    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', views.logout_user, name='logout')
]
