from django.urls import path

from .views import (
    list_repair_products,
    get_product_repair_history,
    create_repair,
    get_products_with_sn,
    delete_repair,
)

urlpatterns = [
    path("list/", list_repair_products, name="repair_list"),
    path("history/", get_product_repair_history, name="repair_history"),
    path("create/", create_repair, name="repair_create"),
    path("products/", get_products_with_sn, name="repair_products"),
    path("delete/", delete_repair, name="repair_delete"),
]