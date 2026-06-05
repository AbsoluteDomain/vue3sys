"""平台-文件路由。

"""

from django.urls import include, path

urlpatterns = [
    path('', include('apps.file.file.urls')),
]
