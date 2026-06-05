# apps/product/products/urls.py

from django.urls import path
from . import views  # 引入同目录下的 views.py

# 定义当前应用的 URL 列表
urlpatterns = [
    # 这里的 '' 表示空路径，也就是匹配到 /api/v1/product/
    # 如果写 path('list/', views.hello_world)，访问路径就是 /api/v1/product/list/
    path('', views.hello_world, name='hello_world'),
    # 访问 /api/v1/product/list/ 时调用 product_list 函数
    path('list/', views.product_list, name='product_list'),
    path('create/', views.create_product, name='create_product'),
    path('update/', views.update_product, name='update_product'),
    path('stock-adjust/', views.stock_adjust_product, name='stock_adjust_product'),
    path('delete/', views.delete_product, name='delete_product'),
]