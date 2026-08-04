from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.finish_product_list, name="finish_product_list"),
    path("daily-stats/", views.finish_product_daily_stats, name="finish_product_daily_stats"),
    path("board-detail/", views.finish_product_board_detail, name="finish_product_board_detail"),
    path("create/", views.create_finish_product, name="create_finish_product"),
    path("update/", views.update_finish_product, name="update_finish_product"),
    path("rollback/", views.rollback_finish_product, name="rollback_finish_product"),
    path("check-joint-consistency/", views.check_joint_stock_consistency, name="check_joint_stock_consistency"),
    path("warehouse-log/list/", views.warehouse_log_list, name="warehouse_log_list"),
    path("bind-joints/", views.bind_joints_to_arm, name="bind_joints_to_arm"),
]
