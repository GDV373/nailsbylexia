from django.urls import path

from . import views


urlpatterns = [
    path("", views.manage_stock, name="manage_stock"),
    path("add/", views.add_stock_item, name="add_stock_item"),
    path("<int:item_id>/edit/", views.edit_stock_item, name="edit_stock_item"),
    path("<int:item_id>/archive/", views.archive_stock_item, name="archive_stock_item"),
    path("<int:item_id>/adjust/", views.adjust_stock, name="adjust_stock"),
    path("lookup/", views.lookup_stock_by_barcode, name="lookup_stock_by_barcode"),
]