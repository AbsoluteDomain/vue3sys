"""系统管理-角色模块。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.exceptions.business import BusinessException
from core.openapi import page_resp, resp
from core.viewsets import BaseModelViewSet
from core.permissions.decorators import permission_required
from core.permissions.perms import HasPerm
from apps.system.menus.models import Menu
from apps.system.roles.models import Role, RoleMenu, RoleDept
from apps.system.users.models import UserRole
from core.permissions.data_scope import data_permission_required
from core.response import error, success

from .serializers import RoleCreateSerializer, RoleFormSerializer, RolePageSerializer
from .filters import RoleFilter


def build_role_page_query(*, keywords: str, start_date, end_date, data_permission):
    """构建角色分页查询条件。

    - 固定过滤：`is_deleted=0`
    - 数据权限：按创建人范围过滤
    - 关键词：角色名/角色编码模糊匹配
    - 时间范围：按创建时间过滤
    """
    query = Q(is_deleted=0)

    if isinstance(data_permission, list) and data_permission:
        query &= Q(create_by__in=data_permission)

    if keywords:
        query &= Q(name__icontains=keywords) | Q(code__icontains=keywords)

    if start_date and end_date:
        start_date_time = parse_datetime(start_date)
        end_date_time = parse_datetime(end_date)
        if start_date_time and end_date_time:
            query &= Q(create_time__gte=start_date_time, create_time__lte=end_date_time)

    return query


def assign_role_menus(*, role_id: int, menu_ids, current_user, updater_user_id):
    role = Role.objects.filter(id=role_id, is_deleted=0).first()
    if role is None:
        raise BusinessException("角色不存在", code="C0113", status=404)

    creator_id = role.create_by if role.create_by is not None else getattr(current_user, "id", None)
    has_permission = data_permission_required(current_user, "update", creator_id)
    if not has_permission:
        raise BusinessException("您没有权限分配此角色的菜单权限", code="A0301", status=403)

    try:
        menu_id_list = [int(menu_id) for menu_id in (menu_ids or []) if menu_id]
    except (ValueError, TypeError):
        raise BusinessException("菜单ID格式不正确", code="A0400", status=400)

    existing_menu_ids = set(Menu.objects.filter(id__in=menu_id_list).values_list("id", flat=True))
    invalid_menu_ids = [str(menu_id) for menu_id in menu_id_list if menu_id not in existing_menu_ids]
    if invalid_menu_ids:
        raise BusinessException(
            f"以下菜单ID不存在: {', '.join(invalid_menu_ids)}",
            code="A0400",
            status=400,
        )

    with transaction.atomic():
        RoleMenu.objects.filter(role_id=role_id).delete()
        role_menu_objs = [RoleMenu(role_id=role_id, menu_id=menu_id) for menu_id in menu_id_list]
        if role_menu_objs:
            RoleMenu.objects.bulk_create(role_menu_objs)

        if updater_user_id:
            role.update_by = updater_user_id
            role.update_time = timezone.now()
            role.save(update_fields=["update_by", "update_time"])

    return {"data": {}, "msg": "菜单权限分配成功"}


def create_role(*, payload: dict, creator_user_id):
    name = payload.get("name")
    code = payload.get("code")

    if Role.objects.filter(Q(name=name) | Q(code=code), is_deleted=0).exists():
        raise BusinessException("角色名称或编码已存在", code="A0400", status=400)

    deleted_role = Role.objects.filter(name=name, code=code, is_deleted=1).first()
    if deleted_role:
        deleted_role.is_deleted = 0
        deleted_role.create_by = creator_user_id
        deleted_role.create_time = timezone.now()
        deleted_role.update_by = None
        deleted_role.update_time = None
        if "sort" in payload:
            deleted_role.sort = payload.get("sort")
        if "status" in payload:
            deleted_role.status = payload.get("status")
        if "dataScope" in payload:
            deleted_role.data_scope = payload.get("dataScope")
        deleted_role.save()
        return {"role": deleted_role, "msg": "角色创建成功"}

    if Role.objects.filter(Q(name=name) | Q(code=code), is_deleted=1).exists():
        raise BusinessException("角色名称或编码已存在（在已删除的角色中）", code="A0400", status=400)

    serializer = RoleCreateSerializer(data=payload)
    if not serializer.is_valid():
        raise BusinessException("参数校验失败", code="A0400", status=400, data=serializer.errors)

    role = serializer.save(create_by=creator_user_id)
    return {"role": role, "msg": "角色创建成功"}


def update_role(*, role_id: int, payload: dict, current_user, updater_user_id):
    role = Role.objects.filter(id=role_id, is_deleted=0).first()
    if role is None:
        raise BusinessException("角色不存在", code="C0113", status=404)

    old_data_scope = role.data_scope

    creator_id = role.create_by if role.create_by is not None else getattr(current_user, "id", None)
    has_permission = data_permission_required(current_user, "update", creator_id)
    if not has_permission:
        raise BusinessException("您没有权限编辑此角色", code="A0301", status=403)

    data = payload.copy() if hasattr(payload, "copy") else dict(payload)
    data["id"] = role_id

    serializer = RoleFormSerializer(role, data=data, partial=True)
    if not serializer.is_valid():
        raise BusinessException("参数校验失败", code="A0400", status=400, data=serializer.errors)

    updated_role = serializer.save()
    if updater_user_id:
        updated_role.update_by = updater_user_id
        updated_role.save(update_fields=["update_by"])

    # 数据权限发生变化时，失效该角色关联用户的登录态（JWT tokenVersion）
    if old_data_scope != updated_role.data_scope:
        from apps.auth.utils.session_utils import invalidate_user_sessions
        from apps.system.users.models import UserRole

        user_ids = (
            UserRole.objects.filter(role_id=role_id)
            .values_list("user_id", flat=True)
            .distinct()
        )
        for uid in user_ids:
            invalidate_user_sessions(int(uid))

    return {"role": updated_role, "msg": "角色更新成功"}


def delete_roles(*, role_id: str, current_user, updater_user_id):
    role_ids = str(role_id)
    if role_ids.isdigit():
        id_list = [int(role_ids)]
    else:
        id_list = [int(id_str) for id_str in role_ids.split(",") if id_str.isdigit()]

    if not id_list:
        raise BusinessException("无效的角色ID", code="A0400", status=400)

    roles = Role.objects.filter(id__in=id_list, is_deleted=0)
    for role in roles:
        if UserRole.objects.filter(role_id=role.id).exists():
            raise BusinessException(f"角色【{role.name}】已分配用户，请先解除关联后删除", code="A0400", status=400)

    authorized_roles = []
    unauthorized_roles = []
    for role in roles:
        creator_id = role.create_by if role.create_by is not None else getattr(current_user, "id", None)
        has_permission = data_permission_required(current_user, "delete", creator_id)
        if has_permission:
            authorized_roles.append(role)
        else:
            unauthorized_roles.append(role.name)

    if unauthorized_roles:
        raise BusinessException(
            f"您没有权限删除以下角色: {', '.join(unauthorized_roles)}",
            code="A0301",
            status=403,
        )

    for role in authorized_roles:
        role.is_deleted = 1
        if updater_user_id:
            role.update_by = updater_user_id
        role.save(update_fields=["is_deleted", "update_by"])

    return {"deleted_count": len(authorized_roles)}


@extend_schema_view(
    list=extend_schema(
        summary="角色分页列表",
        parameters=[
            OpenApiParameter(name="keywords", location=OpenApiParameter.QUERY, required=False, type=str, description="关键词（角色名/编码）"),
            OpenApiParameter(name="startDate", location=OpenApiParameter.QUERY, required=False, type=str, description="开始日期（YYYY-MM-DD）"),
            OpenApiParameter(name="endDate", location=OpenApiParameter.QUERY, required=False, type=str, description="结束日期（YYYY-MM-DD）"),
            OpenApiParameter(name="pageNum", location=OpenApiParameter.QUERY, required=False, type=int, description="页码（默认 1）"),
            OpenApiParameter(name="pageSize", location=OpenApiParameter.QUERY, required=False, type=int, description="每页记录数（默认 10）"),
        ],
        responses=page_resp("RolePageResult", RolePageSerializer(many=True)),
    ),
    retrieve=extend_schema(
        summary="角色详情",
        responses=resp("RoleDetailResult", RoleFormSerializer()),
    ),
    create=extend_schema(
        summary="新增角色",
        request=RoleCreateSerializer,
        responses=resp("RoleCreateResult", RoleFormSerializer()),
    ),
    update=extend_schema(
        summary="更新角色",
        request=RoleFormSerializer,
        responses=resp("RoleUpdateResult", RoleFormSerializer()),
    ),
    destroy=extend_schema(
        summary="删除角色",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="删除角色，多个以英文逗号(,)拼接",
            )
        ],
        responses=resp("RoleDeleteResult", serializers.DictField(required=False)),
    ),
)
@extend_schema(tags=["03.角色接口"])
class RoleViewSet(BaseModelViewSet):
    """系统管理-角色ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = Role.objects.filter(is_deleted=0).order_by("sort", "id")
    filterset_class = RoleFilter

    def get_queryset(self):
        qs = Role.objects.filter(is_deleted=0).exclude(code="ROOT").order_by("sort", "id")

        data_permission = data_permission_required(getattr(self.request, "user", None), "select")
        if isinstance(data_permission, list) and data_permission:
            qs = qs.filter(create_by__in=data_permission)
        return qs

    def get_serializer_class(self):
        if self.action in ["list"]:
            return RolePageSerializer
        if self.action == "create":
            return RoleCreateSerializer
        return RoleFormSerializer

    @permission_required(["sys:role:list"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @permission_required(["sys:role:list"])
    def retrieve(self, request, *args, **kwargs):
        role = self.get_object()

        creator_id = role.create_by if role.create_by is not None else getattr(request.user, "id", None)
        has_permission = data_permission_required(request.user, "select", creator_id)
        if has_permission is False:
            raise PermissionDenied("您没有权限查看此角色")

        serializer = RoleFormSerializer(role)
        return success(serializer.data, msg="获取角色信息成功")

    @permission_required(["sys:role:create"])
    @extend_schema(
        summary="新增角色",
        request=RoleCreateSerializer,
        responses=resp("RoleCreateResult", RoleFormSerializer()),
    )
    def create(self, request, *args, **kwargs):
        creator_user_id = request.user.id if hasattr(request, "user") and request.user else None
        result = create_role(payload=request.data, creator_user_id=creator_user_id)
        role_data = RoleFormSerializer(result["role"]).data
        return success(role_data, msg=result.get("msg", "角色创建成功"))

    @permission_required(["sys:role:update"])
    @extend_schema(
        summary="更新角色",
        request=RoleFormSerializer,
        responses=resp("RoleUpdateResult", RoleFormSerializer()),
    )
    def update(self, request, *args, **kwargs):
        role = self.get_object()
        updater_user_id = request.user.id if hasattr(request, "user") and request.user else None
        result = update_role(role_id=role.id, payload=request.data, current_user=request.user, updater_user_id=updater_user_id)
        updated_data = RoleFormSerializer(result["role"]).data
        return success(updated_data, msg=result.get("msg", "角色更新成功"))

    @permission_required(["sys:role:delete"])
    @extend_schema(
        summary="删除角色",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="角色ID，多个以英文逗号(,)分割",
            )
        ],
        responses=resp("RoleDeleteResult", serializers.DictField(required=False)),
    )
    def destroy(self, request, *args, **kwargs):
        ids = kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        updater_user_id = request.user.id if hasattr(request, "user") and request.user else None
        result = delete_roles(role_id=str(ids), current_user=request.user, updater_user_id=updater_user_id)
        return success({}, msg=f"成功删除 {result['deleted_count']} 个角色")

    @permission_required(["sys:role:update"])
    @action(detail=True, methods=["get"], url_path="dept-ids")
    def dept_ids(self, request, *args, **kwargs):
        role = self.get_object()

        creator_id = role.create_by if role.create_by is not None else getattr(request.user, "id", None)
        has_permission = data_permission_required(request.user, "select", creator_id)
        if has_permission is False:
            raise PermissionDenied("您没有权限查看此角色")

        dept_ids = list(RoleDept.objects.filter(role_id=role.id).values_list("dept_id", flat=True))
        return success([str(dept_id) for dept_id in dept_ids], msg="获取角色自定义部门成功")

    @permission_required(["sys:role:assign"])
    @action(detail=True, methods=["put"], url_path="depts")
    def assign_depts(self, request, *args, **kwargs):
        role = self.get_object()

        creator_id = role.create_by if role.create_by is not None else getattr(request.user, "id", None)
        has_permission = data_permission_required(request.user, "update", creator_id)
        if not has_permission:
            raise PermissionDenied("您没有权限分配此角色的部门权限")

        if not isinstance(request.data, list):
            raise BusinessException("参数格式不正确", code="A0400", status=400)

        try:
            new_dept_ids = [int(v) for v in request.data if v is not None and str(v).strip() != ""]
        except (ValueError, TypeError):
            raise BusinessException("部门ID格式不正确", code="A0400", status=400)

        new_dept_ids = sorted(list({v for v in new_dept_ids if v > 0}))
        old_dept_ids = sorted(
            list(RoleDept.objects.filter(role_id=role.id).values_list("dept_id", flat=True))
        )

        with transaction.atomic():
            RoleDept.objects.filter(role_id=role.id).delete()
            rows = [RoleDept(role_id=role.id, dept_id=dept_id) for dept_id in new_dept_ids]
            if rows:
                RoleDept.objects.bulk_create(rows)

            role.update_time = timezone.now()
            role.update_by = request.user.id if hasattr(request, "user") and request.user else None
            role.save(update_fields=["update_time", "update_by"])

        if old_dept_ids != new_dept_ids:
            from apps.auth.utils.session_utils import invalidate_user_sessions

            user_ids = (
                UserRole.objects.filter(role_id=role.id)
                .values_list("user_id", flat=True)
                .distinct()
            )
            for uid in user_ids:
                invalidate_user_sessions(int(uid))

        return success({}, msg="分配部门权限成功")

    @permission_required(["sys:role:update"])
    @extend_schema(
        summary="修改角色状态",
        parameters=[
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                required=True,
                type=int,
                description="角色状态：1 启用 / 0 禁用（通过 query 参数传入）",
            ),
        ],
        responses=resp("RoleStatusUpdateResult", serializers.DictField(required=False)),
    )
    @action(methods=["put"], detail=True, url_path="status")
    def status(self, request, pk=None, *args, **kwargs):
        try:
            status_value = int(request.query_params.get("status", ""))
        except (ValueError, TypeError):
            return error("状态值格式不正确")
        if status_value not in [0, 1]:
            return error("状态值不正确，应为 0(禁用) 或 1(启用)")

        updater_user_id = request.user.id if hasattr(request, "user") and request.user else None
        result = update_role(
            role_id=int(pk),
            payload={"status": status_value},
            current_user=request.user,
            updater_user_id=updater_user_id,
        )
        return success({}, msg=result.get("msg", "修改角色状态成功"))

    @permission_required(["sys:role:list"])
    @extend_schema(
        summary="角色下拉选项",
        responses=resp(
            "RoleOptionsResult",
            serializers.ListField(child=serializers.DictField()),
        ),
    )
    @action(methods=["get"], detail=False, url_path="options")
    def options(self, request, *args, **kwargs):
        roles = Role.objects.filter(is_deleted=0, status=1).exclude(code="ROOT").order_by("sort", "id")

        options = []
        for role in roles:
            options.append(
                {
                    "value": str(role.id),
                    "label": role.name,
                    "tag": "success" if role.status == 1 else "danger",
                }
            )

        return success(options, msg="获取角色下拉列表成功")

    @permission_required(["sys:role:update"])
    @extend_schema(
        summary="角色表单数据",
        responses=resp("RoleFormResult", RoleFormSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, pk=None, *args, **kwargs):
        role = self.get_object()

        creator_id = role.create_by if role.create_by is not None else getattr(request.user, "id", None)
        has_permission = data_permission_required(request.user, "update", creator_id)
        if has_permission is False:
            raise PermissionDenied("您没有权限编辑此角色")

        serializer = RoleFormSerializer(role)
        return success(serializer.data, msg="获取角色表单信息成功")

    @permission_required(["sys:menu:list"])
    @extend_schema(
        summary="角色菜单ID集合",
        responses=resp(
            "RoleMenuIdsResult",
            serializers.ListField(child=serializers.CharField()),
        ),
    )
    @action(methods=["get"], detail=True, url_path="menu-ids")
    def menu_ids(self, request, pk=None, *args, **kwargs):
        role = self.get_object()
        menu_ids = RoleMenu.objects.filter(role_id=role.id).values_list("menu_id", flat=True)
        return success([str(menu_id) for menu_id in menu_ids])

    @permission_required(["sys:role:update"])
    @extend_schema(
        summary="角色分配菜单权限",
        request=serializers.ListField(child=serializers.IntegerField()),
        responses=resp("RoleMenusUpdateResult", serializers.DictField(required=False)),
    )
    @action(methods=["put"], detail=True, url_path="menus")
    def menus(self, request, pk=None, *args, **kwargs):
        updater_user_id = request.user.id if hasattr(request, "user") and request.user else None
        result = assign_role_menus(
            role_id=int(pk),
            menu_ids=request.data,
            current_user=request.user,
            updater_user_id=updater_user_id,
        )
        return success(result.get("data", {}), msg=result.get("msg", "菜单权限分配成功"))
