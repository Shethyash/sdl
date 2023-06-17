from django.urls import path

from nodes import views

urlpatterns = [
    path('', views.node_list, name='nodes'),
    path('store_feeds', views.store_feeds, name='store_feeds'),
    path('get_feeds_chart/<int:node_id>', views.get_feeds, name='get_feeds'),
    path('get_feeds_table/<int:node_id>', views.get_feeds_table, name='get_feeds_table'),
    path('crud/', views.CrudNodes.as_view()),
    path('delete_node/<int:node_id>', views.delete_node, name='delete_node'),
    path('get_chart/<int:node_id>', views.get_chart_data, name='get_chart'),
    path('upload_image/<int:node_id>', views.crop_image_upload, name='upload_image'),
    path('crop_image_gallery/<int:node_id>', views.crop_image_gallery, name='crop_image_gallery'),
    path('import-csv/<int:node_id>', views.import_csv, name='import_csv'),
]
