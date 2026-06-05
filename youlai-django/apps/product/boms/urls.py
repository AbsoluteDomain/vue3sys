from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.bom_list, name="bom_list"),
    path("detail/", views.bom_detail, name="bom_detail"),
    path("create/", views.create_bom, name="create_bom"),
    path("update/", views.update_bom, name="update_bom"),
    path("delete/", views.delete_bom, name="delete_bom"),
    path("assemble/", views.assemble_bom, name="assemble_bom"),
]
