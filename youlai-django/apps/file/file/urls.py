"""平台-文件路由。

"""

from django.urls import path

from .views import FileViewSet

urlpatterns = [
    path("", FileViewSet.as_view({"post": "create", "delete": "destroy"}), name="file_upload"),
]
