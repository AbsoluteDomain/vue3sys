"""系统管理-字典视图。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.shortcuts import get_object_or_404

from core.openapi import page_resp, resp
from core.permissions.perms import HasPerm
from core.permissions.decorators import permission_required
from core.viewsets import BaseModelViewSet
from apps.system.dicts.models import Dictionary, DictionaryItem
from core.permissions.data_scope import data_permission_required
from core.response import error, page_success, success

from .filters import DictFilter, DictItemFilter
from .serializers import (
    DictCreateSerializer,
    DictDetailSerializer,
    DictItemCreateSerializer,
    DictItemSerializer,
    DictItemUpdateSerializer,
    DictListSerializer,
    DictUpdateSerializer,
)


@extend_schema(tags=["06.字典接口"])
class DictViewSet(BaseModelViewSet):
    """系统管理-字典ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = Dictionary.objects.filter(is_deleted=0).order_by("-id")
    filterset_class = DictFilter

    def get_queryset(self):
        qs = Dictionary.objects.filter(is_deleted=0).order_by("-id")

        data_permission = data_permission_required(getattr(self.request, "user", None), "select")
        if isinstance(data_permission, list) and data_permission:
            qs = qs.filter(create_by__in=data_permission)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return DictListSerializer
        if self.action == "create":
            return DictCreateSerializer
        if self.action in ["update", "partial_update"]:
            return DictUpdateSerializer
        if self.action == "form":
            return DictDetailSerializer
        return DictListSerializer

    @permission_required(["sys:dict:list"])
    @extend_schema(
        summary="字典列表",
        responses=resp("DictOptionListResult", serializers.ListField(child=serializers.DictField())),
    )
    @action(methods=["get"], detail=False, url_path="options")
    def options(self, request, *args, **kwargs):
        qs = Dictionary.objects.filter(is_deleted=0, status=1).order_by("-id")
        data = [{"value": d.dict_code, "label": d.name} for d in qs]
        return success(data)

    @permission_required(["sys:dict:list"])
    @extend_schema(
        summary="获取字典分页列表",
        description="根据关键词分页查询字典数据。\n\n支持查询参数：keywords（关键字），pageNum（页码，默认1），pageSize（每页记录数，默认10）。",
        parameters=[
            OpenApiParameter(name="keywords", location=OpenApiParameter.QUERY, description="关键字（字典名称或编码）", required=False, type=str),
            OpenApiParameter(name="pageNum", location=OpenApiParameter.QUERY, description="页码（默认1）", required=False, type=int),
            OpenApiParameter(name="pageSize", location=OpenApiParameter.QUERY, description="每页记录数（默认10）", required=False, type=int),
        ],
        responses=page_resp("DictPageResult", DictListSerializer(many=True)),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @permission_required(["sys:dict:create"])
    @extend_schema(
        summary="创建字典",
        request=DictCreateSerializer,
        responses=resp("DictCreateResult", DictDetailSerializer()),
    )
    def create(self, request, *args, **kwargs):
        user_id = request.user.id if hasattr(request, "user") and request.user else None
        serializer = DictCreateSerializer(data=request.data, context={"user_id": user_id})
        if serializer.is_valid():
            dict_obj = serializer.save()
            response_serializer = DictDetailSerializer(dict_obj)
            return success(response_serializer.data, msg="字典创建成功")
        return error(serializer.errors, code="A0400", status=400)

    @permission_required(["sys:dict:update"])
    @extend_schema(
        summary="更新字典",
        request=DictUpdateSerializer,
        responses=resp("DictUpdateResult", DictDetailSerializer()),
    )
    def update(self, request, *args, **kwargs):
        dict_obj = self.get_object()

        has_permission = data_permission_required(request.user, "update", dict_obj.create_by)
        if has_permission is False:
            raise PermissionDenied("无权限修改此字典")

        user_id = request.user.id if hasattr(request, "user") and request.user else None
        serializer = DictUpdateSerializer(dict_obj, data=request.data, context={"user_id": user_id})
        if serializer.is_valid():
            updated_dict = serializer.save()
            response_serializer = DictDetailSerializer(updated_dict)
            return success(response_serializer.data, msg="字典更新成功")
        return error(serializer.errors, code="A0400", status=400)

    @permission_required(["sys:dict:delete"])
    @extend_schema(
        summary="删除字典",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                description="字典ID，多个以英文逗号(,)分割",
                required=True,
                type=str,
            ),
        ],
        responses=resp("DictDeleteResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def destroy(self, request, *args, **kwargs):
        ids = kwargs.get(self.lookup_url_kwarg or self.lookup_field)

        if not ids:
            return error("请指定要删除的字典ID", code="A0400", status=400)

        dict_ids = str(ids).split(",")
        try:
            dict_ids = [int(did) for did in dict_ids if did]
        except ValueError:
            return error("字典ID格式不正确", code="A0400", status=400)

        if not dict_ids:
            return error("请指定要删除的字典ID", code="A0400", status=400)

        dicts_to_delete = Dictionary.objects.filter(id__in=dict_ids, is_deleted=0)

        dict_codes = dicts_to_delete.values_list("dict_code", flat=True)
        if dict_codes:
            items_count = DictionaryItem.objects.filter(dict_code__in=dict_codes).count()
            if items_count > 0:
                return error("无法删除，存在关联的字典项", code="A0400", status=400)

        unauthorized_dicts = []
        for dict_obj in dicts_to_delete:
            has_permission = data_permission_required(request.user, "delete", dict_obj.create_by)
            if has_permission is False:
                unauthorized_dicts.append(dict_obj.name)
        if unauthorized_dicts:
            raise PermissionDenied(f"无权限删除字典：{', '.join(unauthorized_dicts)}")

        delete_count = dicts_to_delete.count()
        dicts_to_delete.update(is_deleted=1)
        return success({}, msg=f"成功删除{delete_count}个字典")

    @permission_required(["sys:dict:list"])
    @extend_schema(
        summary="获取字典表单数据",
        responses=resp("DictFormResult", DictDetailSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, pk=None, *args, **kwargs):
        dict_obj = get_object_or_404(Dictionary, id=pk, is_deleted=0)

        has_permission = data_permission_required(request.user, "select", dict_obj.create_by)
        if has_permission is False:
            raise PermissionDenied("无权限查看此字典")

        serializer = DictDetailSerializer(dict_obj)
        form_data = {
            "id": serializer.data.get("id"),
            "name": serializer.data.get("name"),
            "dictCode": serializer.data.get("dictCode"),
            "remark": serializer.data.get("remark"),
            "status": serializer.data.get("status"),
        }
        return success(form_data)


@extend_schema(tags=["06.字典接口"])
class DictItemViewSet(BaseModelViewSet):
    """系统管理-字典ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = DictionaryItem.objects.all().order_by("sort")
    lookup_url_kwarg = "item_id"
    filterset_class = DictItemFilter

    def get_serializer_class(self):
        if self.action == "create":
            return DictItemCreateSerializer
        if self.action in ["update", "partial_update"]:
            return DictItemUpdateSerializer
        return DictItemSerializer

    def get_queryset(self):
        dict_code = self.kwargs.get("dict_code")
        qs = DictionaryItem.objects.all().order_by("sort")
        if dict_code:
            qs = qs.filter(dict_code=dict_code)

        data_permission = data_permission_required(getattr(self.request, "user", None), "select")
        if isinstance(data_permission, list) and data_permission:
            qs = qs.filter(create_by__in=data_permission)
        return qs

    @permission_required(["sys:dict-item:list"])
    @extend_schema(
        summary="字典项下拉选项",
        parameters=[
            OpenApiParameter(name="dict_code", location=OpenApiParameter.PATH, description="字典编码", required=True, type=str),
        ],
        responses=resp("DictItemOptionsResult", serializers.JSONField(required=False, allow_null=True)),
    )
    @action(methods=["get"], detail=False, url_path="options")
    def options(self, request, *args, **kwargs):
        dict_code = kwargs.get("dict_code")
        if not dict_code:
            return error("缺少字典编码", code="A0400", status=400)

        if not Dictionary.objects.filter(dict_code=dict_code, is_deleted=0).exists():
            return error(f"字典编码 '{dict_code}' 不存在", code="A0404", status=404)

        dict_items = DictionaryItem.objects.filter(dict_code=dict_code, status=1).order_by("sort")
        result_list = []
        for item in dict_items:
            result_list.append({
                "value": item.value,
                "label": item.label,
                "tagType": item.tag_type,
            })
        return success(result_list)

    @permission_required(["sys:dict-item:list"])
    @extend_schema(
        summary="字典项分页",
        parameters=[
            OpenApiParameter(name="dict_code", location=OpenApiParameter.PATH, description="字典编码", required=True, type=str),
            OpenApiParameter(name="keywords", location=OpenApiParameter.QUERY, description="关键字", required=False, type=str),
            OpenApiParameter(name="pageNum", location=OpenApiParameter.QUERY, description="页码（默认1）", required=False, type=int),
            OpenApiParameter(name="pageSize", location=OpenApiParameter.QUERY, description="每页记录数（默认10）", required=False, type=int),
        ],
        responses=page_resp("DictItemPageResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def list(self, request, dict_code=None, *args, **kwargs):
        if not dict_code:
            return error("缺少字典编码", code="A0400", status=400)

        if not Dictionary.objects.filter(dict_code=dict_code, is_deleted=0).exists():
            return error(f"字典编码 '{dict_code}' 不存在", code="A0404", status=404)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = DictItemSerializer(page, many=True)
            data = []
            for item in serializer.data:
                data.append(
                    {
                        "id": item.get("id"),
                        "dictCode": item.get("dictCode"),
                        "label": item.get("label"),
                        "value": item.get("value"),
                        "sort": item.get("sort"),
                        "status": item.get("status"),
                    }
                )
            return self.get_paginated_response(data)

        serializer = DictItemSerializer(queryset, many=True)
        result_list = []
        for item in serializer.data:
            result_list.append(
                {
                    "id": item.get("id"),
                    "dictCode": item.get("dictCode"),
                    "label": item.get("label"),
                    "value": item.get("value"),
                    "sort": item.get("sort"),
                    "status": item.get("status"),
                }
            )
        return success(result_list)

    @permission_required(["sys:dict-item:list"])
    @extend_schema(
        summary="字典项表单",
        parameters=[
            OpenApiParameter(name="dict_code", location=OpenApiParameter.PATH, description="字典编码", required=True, type=str),
            OpenApiParameter(name="item_id", location=OpenApiParameter.PATH, description="字典项ID", required=True, type=int),
        ],
        responses=resp("DictItemFormResult", DictItemSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, dict_code=None, item_id=None, *args, **kwargs):
        if not Dictionary.objects.filter(dict_code=dict_code, is_deleted=0).exists():
            return error(f"字典编码 '{dict_code}' 不存在", code="A0404", status=404)

        dict_item = get_object_or_404(DictionaryItem, id=item_id, dict_code=dict_code)

        has_permission = data_permission_required(request.user, "select", dict_item.create_by)
        if has_permission is False:
            raise PermissionDenied("无权限查看此字典项")

        serializer = DictItemSerializer(dict_item)
        return success(serializer.data)

    @permission_required(["sys:dict-item:create"])
    @extend_schema(
        summary="创建字典项",
        request=DictItemCreateSerializer,
        parameters=[
            OpenApiParameter(name="dict_code", location=OpenApiParameter.PATH, description="字典编码", required=True, type=str),
        ],
        responses=resp("DictItemCreateResult", DictItemSerializer()),
    )
    def create(self, request, *args, **kwargs):
        dict_code = kwargs.get("dict_code")
        if not dict_code:
            return error("缺少字典编码", code="A0400", status=400)

        dict_obj = Dictionary.objects.filter(dict_code=dict_code, is_deleted=0).first()
        if not dict_obj:
            return error(f"字典编码 '{dict_code}' 不存在", code="A0404", status=404)

        has_permission = data_permission_required(request.user, "add", dict_obj.create_by)
        if has_permission is False:
            raise PermissionDenied("无权限向此字典添加项")

        user_id = request.user.id if hasattr(request, "user") and request.user else None
        request_data = request.data.copy()
        request_data["dictCode"] = dict_code

        serializer = DictItemCreateSerializer(data=request_data, context={"user_id": user_id})
        if serializer.is_valid():
            dict_item = serializer.save()
            response_serializer = DictItemSerializer(dict_item)
            return success(response_serializer.data, msg="字典项创建成功")
        return error(serializer.errors, code="A0400", status=400)

    @permission_required(["sys:dict-item:update"])
    @extend_schema(
        summary="更新字典项",
        request=DictItemUpdateSerializer,
        parameters=[
            OpenApiParameter(name="dict_code", location=OpenApiParameter.PATH, description="字典编码", required=True, type=str),
            OpenApiParameter(name="item_id", location=OpenApiParameter.PATH, description="字典项ID", required=True, type=int),
        ],
        responses=resp("DictItemUpdateResult", DictItemSerializer()),
    )
    def update(self, request, *args, **kwargs):
        dict_code = kwargs.get("dict_code")
        item_id = kwargs.get("item_id")

        if not Dictionary.objects.filter(dict_code=dict_code, is_deleted=0).exists():
            return error(f"字典编码 '{dict_code}' 不存在", code="A0404", status=404)

        dict_item = get_object_or_404(DictionaryItem, id=item_id, dict_code=dict_code)

        has_permission = data_permission_required(request.user, "update", dict_item.create_by)
        if has_permission is False:
            raise PermissionDenied("无权限修改此字典项")

        user_id = request.user.id if hasattr(request, "user") and request.user else None
        request_data = request.data.copy()
        request_data["dictCode"] = dict_code

        serializer = DictItemUpdateSerializer(dict_item, data=request_data, context={"user_id": user_id})
        if serializer.is_valid():
            updated_dict_item = serializer.save()
            response_serializer = DictItemSerializer(updated_dict_item)
            return success(response_serializer.data, msg="字典项更新成功")
        return error(serializer.errors, code="A0400", status=400)

    @permission_required(["sys:dict-item:delete"])
    @extend_schema(
        summary="删除字典项",
        parameters=[
            OpenApiParameter(name="dict_code", location=OpenApiParameter.PATH, description="字典编码", required=True, type=str),
            OpenApiParameter(name="item_id", location=OpenApiParameter.PATH, description="字典项ID，多个以英文逗号(,)分割", required=True, type=str),
        ],
        responses=resp("DictItemDeleteResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def destroy(self, request, *args, **kwargs):
        dict_code = kwargs.get("dict_code")
        item_id = kwargs.get("item_id")

        if not dict_code:
            return error("缺少字典编码", code="A0400", status=400)
        if not item_id:
            return error("请指定要删除的字典项ID", code="A0400", status=400)

        if not Dictionary.objects.filter(dict_code=dict_code, is_deleted=0).exists():
            return error(f"字典编码 '{dict_code}' 不存在", code="A0404", status=404)

        item_id_list = str(item_id).split(",")
        try:
            item_id_list = [int(i) for i in item_id_list if i]
        except ValueError:
            return error("字典项ID格式不正确", code="A0400", status=400)

        if not item_id_list:
            return error("请指定要删除的字典项ID", code="A0400", status=400)

        items_to_delete = DictionaryItem.objects.filter(id__in=item_id_list, dict_code=dict_code)
        if items_to_delete.count() != len(item_id_list):
            found_ids = set(items_to_delete.values_list("id", flat=True))
            missing_ids = [str(i) for i in item_id_list if i not in found_ids]
            return error(f"未找到ID为 {', '.join(missing_ids)} 的字典项", code="A0404", status=404)

        unauthorized_items = []
        for item in items_to_delete:
            has_permission = data_permission_required(request.user, "delete", item.create_by)
            if has_permission is False:
                unauthorized_items.append(f"{item.label}(ID:{item.id})")
        if unauthorized_items:
            return error(
                f"无权限删除以下字典项：{', '.join(unauthorized_items)}",
                code="A0301",
                status=403,
            )

        delete_count = items_to_delete.count()
        items_to_delete.delete()
        return success({}, msg=f"成功删除{delete_count}个字典项")
