"""系统管理-部门视图。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.system.dept.models import Department
from core.permissions.decorators import permission_required
from core.permissions.perms import HasPerm
from core.permissions.data_scope import data_permission_required, DataPermission, apply_data_permission
from core.response import error, success
from core.openapi import resp
from core.viewsets import BaseModelViewSet
from .filters import DeptFilter
from .serializers import DeptSerializer, DeptCreateSerializer, DeptUpdateSerializer, DeptFormSerializer
from django.shortcuts import get_object_or_404


@extend_schema(tags=["05.部门接口"])
class DeptViewSet(BaseModelViewSet):
    """系统管理-部门ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = Department.objects.filter(is_deleted=0).order_by('sort', 'id')
    filterset_class = DeptFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return DeptCreateSerializer
        if self.action in ['update', 'partial_update']:
            return DeptUpdateSerializer
        if self.action == 'form':
            return DeptFormSerializer
        return DeptSerializer

    @permission_required(["sys:dept:list"])
    @extend_schema(
        summary="部门树形列表",
        parameters=[
            OpenApiParameter(
                name="keywords",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="关键词（部门名称）",
            ),
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="部门状态：1 启用 / 0 禁用",
            ),
        ],
        responses=resp("DeptTreeResult", DeptSerializer(many=True)),
    )
    @DataPermission(dept_field="id", user_field="create_by")
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        keywords = request.query_params.get('keywords', '')

        status = request.query_params.get('status')
        dept_status = None
        if status is not None and status != "":
            try:
                dept_status = int(status)
            except ValueError:
                dept_status = None

        dept_list = list(queryset.order_by('sort', 'id'))
        if not dept_list:
            return success([], msg="获取部门列表成功")

        dept_ids = {d.id for d in dept_list}
        parent_ids = {d.parent_id for d in dept_list}
        root_ids = [pid for pid in parent_ids if pid not in dept_ids]

        context = {'status': dept_status, 'allowed_ids': dept_ids}
        serializer = DeptSerializer(dept_list, many=True, context=context)
        data = serializer.data

        if not root_ids:
            return success(data, msg="获取部门列表成功")

        root_id_set = {str(rid) for rid in root_ids}
        result = [item for item in data if item.get('parentId') in root_id_set]
        return success(result, msg="获取部门列表成功")

    @permission_required(["sys:dept:create"])
    @extend_schema(
        summary="新增部门",
        request=DeptCreateSerializer,
        responses=resp("DeptCreateResult", DeptSerializer()),
    )
    def create(self, request, *args, **kwargs):
        user_id = request.user.id if hasattr(request, "user") and request.user else None
        serializer = DeptCreateSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            dept = serializer.save()
            return success(DeptSerializer(dept).data, msg="部门创建成功")
        return error(serializer.errors)

    @permission_required(["sys:dept:update"])
    @extend_schema(
        summary="更新部门",
        request=DeptUpdateSerializer,
        responses=resp("DeptUpdateResult", DeptSerializer()),
    )
    def update(self, request, *args, **kwargs):
        dept = self.get_object()

        if not apply_data_permission(
            Department.objects.filter(id=dept.id, is_deleted=0),
            request.user,
            dept_field="id",
            user_field="create_by",
        ).exists():
            raise PermissionDenied("无权限修改此部门")

        user_id = request.user.id if hasattr(request, "user") and request.user else None
        serializer = DeptUpdateSerializer(dept, data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            updated_dept = serializer.save()
            return success(DeptSerializer(updated_dept).data, msg="部门更新成功")
        return error(serializer.errors)

    @permission_required(["sys:dept:delete"])
    @extend_schema(
        summary="删除部门",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="部门ID，多个以英文逗号(,)分割",
            ),
        ],
        responses=resp("DeptDeleteResult", serializers.DictField(required=False)),
    )
    def destroy(self, request, *args, **kwargs):
        ids = kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        if not ids:
            return error("请指定要删除的部门ID")

        dept_ids = str(ids).split(',')
        try:
            dept_ids = [int(did) for did in dept_ids if did]
        except ValueError:
            return error("部门ID格式不正确")

        if not dept_ids:
            return error("请指定要删除的部门ID")

        depts_to_delete = Department.objects.filter(id__in=dept_ids, is_deleted=0)

        child_depts = Department.objects.filter(parent_id__in=dept_ids, is_deleted=0)
        if child_depts.exists():
            return error("存在子部门，无法删除")

        unauthorized_depts = []
        for dept in depts_to_delete:
            if not apply_data_permission(
                Department.objects.filter(id=dept.id, is_deleted=0),
                request.user,
                dept_field="id",
                user_field="create_by",
            ).exists():
                unauthorized_depts.append(dept.name)
        if unauthorized_depts:
            raise PermissionDenied(f"无权限删除部门：{', '.join(unauthorized_depts)}")

        count = depts_to_delete.count()
        depts_to_delete.update(is_deleted=1)
        return success({}, msg=f"成功删除{count}个部门")

    @permission_required(["sys:dept:list"])
    @extend_schema(
        summary="部门下拉选项",
        responses=resp("DeptOptionsResult", serializers.ListField(child=serializers.DictField())),
    )
    @action(methods=["get"], detail=False, url_path="options")
    @DataPermission(dept_field="id", user_field="create_by")
    def options(self, request, *args, **kwargs):
        queryset = self.filter_queryset(
            Department.objects.filter(is_deleted=0, status=1).order_by("sort", "id")
        )
        root_depts = queryset.filter(parent_id=0)

        result = []
        for dept in root_depts:
            dept_option = {
                "value": str(dept.id),
                "label": dept.name,
            }
            children = self._get_children_options(queryset, dept.id)
            if children:
                dept_option["children"] = children
            result.append(dept_option)

        return success(result)

    def _get_children_options(self, queryset, parent_id):
        child_depts = queryset.filter(parent_id=parent_id)

        result = []
        for dept in child_depts:
            dept_option = {
                "value": str(dept.id),
                "label": dept.name,
            }
            children = self._get_children_options(queryset, dept.id)
            if children:
                dept_option["children"] = children
            result.append(dept_option)

        return result

    @permission_required(["sys:dept:list"])
    @extend_schema(
        summary="部门表单数据",
        responses=resp("DeptFormResult", DeptFormSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, pk=None, *args, **kwargs):
        dept = get_object_or_404(Department, id=pk, is_deleted=0)

        if not apply_data_permission(
            Department.objects.filter(id=dept.id, is_deleted=0),
            request.user,
            dept_field="id",
            user_field="create_by",
        ).exists():
            raise PermissionDenied("无权限查看此部门")

        serializer = DeptFormSerializer(dept)
        return success(serializer.data)
