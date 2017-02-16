from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

app_name = 'upload'
urlpatterns = [
    url(r'^$', views.upload, name='index'),
    url(r'^upload-file/$', views.upload_file, name='upload_file'),
    url(r'^add-metadata/$', views.add_metadata, name='add_metadata'),
    url(r'^categorize/$', views.categorize, name='categorize'),
    url(r'^tables/(?P<id>[0-9]+)/$', views.table_detail, name='detail'),
    url(r'^write-to-db/$', views.write_to_db, name='write_to_db'),
    url(r'^check-task-status/$', views.check_task_status, name='check_status'),
    url(r'^login/$', auth_views.login, name='login'),
    url(r'^logout/$', views.logout_user, name='logout')
]
