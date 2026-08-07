# apps/order/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # 订单列表查询（数据库）
    path("list/", views.order_list, name="order_list"),
    # 健康检查（外部接口代理）
    path("health/", views.order_health_check, name="order_health_check"),
    # 全量查询（外部接口代理，支持可选 start_date, end_date）
    path("sync/all/", views.order_sync_all, name="order_sync_all"),
    # 查询当天（外部接口代理）
    path("sync/today/", views.order_sync_today, name="order_sync_today"),
    # 增量查询（外部接口代理，日期拼接到URL）
    path("sync/since/<str:since_date>/", views.order_sync_since, name="order_sync_since"),
    # 按订单号查询（外部接口代理，订单号拼接到URL）
    path("by-no/<str:order_no>/", views.order_by_no, name="order_by_no"),
]
