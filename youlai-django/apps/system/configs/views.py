"""系统管理-系统配置视图。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.system.configs.models import SysConfig
from core.permissions.decorators import permission_required
from core.permissions.perms import HasPerm
from core.response import error, page_success, success
from core.openapi import page_resp, resp
from core.viewsets import BaseModelViewSet
from .filters import ConfigFilter
from .serializers import ConfigPageSerializer, ConfigFormSerializer, ConfigCreateSerializer, ConfigUpdateSerializer
from django.shortcuts import get_object_or_404
from django.core.cache import cache


@extend_schema(tags=["07.系统配置"])
class ConfigViewSet(BaseModelViewSet):
    """系统管理-系统配置ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = SysConfig.objects.filter(is_deleted=0).order_by("-create_time")
    filterset_class = ConfigFilter

    def get_serializer_class(self):
        if self.action == "list":
            return ConfigPageSerializer
        if self.action == "create":
            return ConfigCreateSerializer
        if self.action in ["update", "partial_update"]:
            return ConfigUpdateSerializer
        if self.action == "form":
            return ConfigFormSerializer
        return ConfigPageSerializer

    @permission_required(["sys:config:list"])
    @extend_schema(
        summary="系统配置分页列表",
        parameters=[
            OpenApiParameter(
                name="configName",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="配置名称关键字",
            ),
            OpenApiParameter(
                name="configKey",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="配置键关键字",
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
        responses=page_resp("ConfigPageResult", ConfigPageSerializer(many=True)),
    )
    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        if isinstance(getattr(resp, "data", None), dict) and "msg" in resp.data:
            resp.data["msg"] = "操作成功"
        return resp

    @permission_required(["sys:config:create"])
    @extend_schema(
        summary="新增系统配置",
        request=ConfigCreateSerializer,
        responses=resp("ConfigCreateResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def create(self, request, *args, **kwargs):
        serializer = ConfigCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return error(serializer.errors, code="A0400", status=400)

        serializer.save()
        cache.delete("sys_config_all")
        return success(None, msg="新增成功")

    @permission_required(["sys:config:update"])
    @extend_schema(
        summary="修改系统配置",
        request=ConfigUpdateSerializer,
        responses=resp("ConfigUpdateResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def update(self, request, *args, **kwargs):
        config = self.get_object()
        serializer = ConfigUpdateSerializer(config, data=request.data, context={"request": request}, partial=True)
        if not serializer.is_valid():
            return error(serializer.errors, code="A0400", status=400)

        serializer.save()
        cache.delete("sys_config_all")
        return success(None, msg="修改成功")

    @permission_required(["sys:config:delete"])
    @extend_schema(
        summary="删除系统配置",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="配置ID，多个以英文逗号(,)分割",
            ),
        ],
        responses=resp("ConfigDeleteResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def destroy(self, request, *args, **kwargs):
        ids = kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        if not ids:
            return error("请指定要删除的配置ID", code="A0400", status=400)

        id_list = str(ids).split(",")
        try:
            id_list = [int(i) for i in id_list if i]
        except ValueError:
            return error("配置ID格式不正确", code="A0400", status=400)

        if not id_list:
            return error("请指定要删除的配置ID", code="A0400", status=400)

        configs = SysConfig.objects.filter(id__in=id_list, is_deleted=0)
        for config in configs:
            config.is_deleted = 1
            config.update_by = request.user.id if hasattr(request, "user") and request.user else None
            config.save(update_fields=["is_deleted", "update_by"])

        cache.delete("sys_config_all")
        return success(None, msg="删除成功")

    @permission_required(["sys:config:list"])
    @extend_schema(
        summary="系统配置表单数据",
        responses=resp("ConfigFormResult", ConfigFormSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, pk=None, *args, **kwargs):
        config = get_object_or_404(SysConfig, id=pk, is_deleted=0)
        serializer = ConfigFormSerializer(config)
        return success(serializer.data, msg="操作成功")

    @permission_required(["sys:config:refresh"])
    @extend_schema(
        summary="刷新系统配置缓存",
        responses=resp("ConfigRefreshResult", serializers.JSONField(required=False, allow_null=True)),
    )
    @action(methods=["put"], detail=False, url_path="refresh")
    def refresh(self, request, *args, **kwargs):
        cache.delete("sys_config_all")
        configs = SysConfig.objects.filter(is_deleted=0)
        config_dict = {config.config_key: config.config_value for config in configs}
        cache.set("sys_config_all", config_dict, timeout=3600)
        return success(None, msg="刷新缓存成功")
