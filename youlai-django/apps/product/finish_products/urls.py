from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.finish_product_list, name="finish_product_list"),
    path("daily-stats/", views.finish_product_daily_stats, name="finish_product_daily_stats"),
    path("board-detail/", views.finish_product_board_detail, name="finish_product_board_detail"),
    path("update/", views.update_finish_product, name="update_finish_product"),
    path("rollback/", views.rollback_finish_product, name="rollback_finish_product"),
]
