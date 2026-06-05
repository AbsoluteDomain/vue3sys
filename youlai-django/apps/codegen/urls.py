"""平台-代码生成路由。

"""

from django.urls import path

from .views import CodegenConfigView, CodegenDownloadView, CodegenPreviewView, CodegenTablePageView

urlpatterns = [
    path("table", CodegenTablePageView.as_view({"get": "page"}), name="codegen_table_page"),
    path(
        "<str:table_name>/config",
        CodegenConfigView.as_view({"get": "retrieve", "post": "create"}),
        name="codegen_config",
    ),
    path(
        "<str:table_name>/preview",
        CodegenPreviewView.as_view({"get": "retrieve"}),
        name="codegen_preview",
    ),
    path(
        "<str:table_name>/download",
        CodegenDownloadView.as_view({"get": "retrieve"}),
        name="codegen_download",
    ),
]
