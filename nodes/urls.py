from nodes import views

from django.urls import path, include
from django.conf.urls import url

urlpatterns = [
    path('', views.node, name='nodes'),
    path('store_feeds', views.store_feeds, name='store_feeds'),
    path('get_feeds', views.get_feeds, name='get_feeds'),
    path('nodereg', views.nodereg, name='nodereg'),
    path('node_edit', views.edit_node, name='edit_node'),
]
