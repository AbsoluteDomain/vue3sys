"""文件管理路由。

"""
from django.urls import path

from . import manager_views

urlpatterns = [
    path("list", manager_views.file_list, name="file_manager_list"),
    path("breadcrumb", manager_views.file_breadcrumb, name="file_manager_breadcrumb"),
    path("upload", manager_views.file_upload, name="file_manager_upload"),
    path("folder", manager_views.file_create_folder, name="file_manager_folder"),
    path("delete", manager_views.file_delete, name="file_manager_delete"),
    path("restore", manager_views.file_restore, name="file_manager_restore"),
    path("purge", manager_views.file_purge, name="file_manager_purge"),
    path("download", manager_views.file_download, name="file_manager_download"),
]
