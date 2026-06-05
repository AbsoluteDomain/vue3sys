"""系统管理-日志视图。

Author: Ray.Hao
Version: 0.0.1
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from core.pagination import StandardResultsPagination
from core.openapi import page_resp, resp
from core.viewsets import BaseModelViewSet
from apps.system.logs.models import Log
from core.permissions.decorators import permission_required
from core.permissions.perms import HasPerm
from core.response import error, success
from .filters import LogFilter
from .serializers import LogPageSerializer


@extend_schema(tags=["09.日志接口"])
class LogViewSet(BaseModelViewSet):
    """系统管理-日志ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    pagination_class = StandardResultsPagination
    queryset = Log.objects.order_by("-create_time")
    filterset_class = LogFilter

    def get_serializer_class(self):
        return LogPageSerializer

    @extend_schema(
        summary="日志分页列表",
        parameters=[
            OpenApiParameter(
                name="keywords",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="关键词（content/request_uri/method/province/city/browser/os 多字段匹配）",
            ),
            OpenApiParameter(
                name="createTime",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="创建时间范围：start,end（格式：YYYY-MM-DD HH:mm:ss）",
            ),
            OpenApiParameter(
                name="pageNum",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="页码（默认 1）",
            ),
            OpenApiParameter(
                name="pageSize",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="每页记录数（默认 10）",
            ),
        ],
        responses=page_resp("LogPageResult", LogPageSerializer(many=True)),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


