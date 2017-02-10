from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.search),
    url(r'^detail/$', views.search_detail),
    url(r'^get-all-results/$', views.get_all_results, name='get_all_results'),
]

