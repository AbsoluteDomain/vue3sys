"""Django 项目 URL 路由配置。

"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def handler404(request, exception):
    return JsonResponse({"code": "C0113", "msg": "接口不存在", "data": None}, status=404)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # path('api/v1/product/', include('apps.product.products.urls')),
    re_path(r"^api/v1/auth/?", include("apps.auth.urls")),
    re_path(r"^api/v1/codegen/?", include("apps.codegen.urls")),
    re_path(r"^api/v1/files/?", include("apps.file.urls")),
    re_path(r"^api/v1/users/?", include("apps.system.users.urls")),
    re_path(r"^api/v1/roles/?", include("apps.system.roles.urls")),
    re_path(r"^api/v1/menus/?", include("apps.system.menus.urls")),
    re_path(r"^api/v1/depts/?", include("apps.system.dept.urls")),
    re_path(r"^api/v1/dicts/?", include("apps.system.dicts.urls")),
    re_path(r"^api/v1/configs/?", include("apps.system.configs.urls")),
    re_path(r"^api/v1/notices/?", include("apps.system.notices.urls")),
    re_path(r"^api/v1/logs/?", include("apps.system.logs.urls")),
    re_path(r"^api/v1/statistics/?", include("apps.system.statistics.urls")),
    re_path(r"^api/v1/operation-logs/?", include("apps.system.operation_logs.urls")),
    # 新增的路由
    re_path(r"^api/v1/product/?", include("apps.product.products.urls")),
    re_path(r"^api/v1/bom/?", include("apps.product.boms.urls")),
]
