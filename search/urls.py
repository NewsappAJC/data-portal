from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.search),
    url(r'^detail/$', views.search_detail),
    url(r'^get-presigned-url/(?P<id>[0-9]+)/$', views.get_presigned_url, name='get_presigned_url'),
]

