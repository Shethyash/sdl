from nodes import views

from django.urls import path

urlpatterns = [
    path('', views.node_list, name='nodes'),
    path('store_feeds/', views.store_feeds, name='store_feeds'),
    path('get_feeds/<int:id>', views.get_feeds, name='get_feeds'),
    path('crud/', views.CrudNodes.as_view()),
]
