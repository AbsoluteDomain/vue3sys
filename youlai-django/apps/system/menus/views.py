"""系统管理-菜单视图。

"""

from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from django.shortcuts import get_object_or_404
from apps.system.menus.models import Menu
from apps.system.roles.models import RoleMenu
from apps.system.users.models import UserRole
from core.permissions.decorators import permission_required
from core.permissions.perms import HasPerm
from core.response import error, success
from core.openapi import resp
from core.viewsets import BaseModelViewSet
from .filters import MenuFilter
from .serializers import (
    MenuSerializer, MenuOptionSerializer, MenuCreateSerializer,
    MenuUpdateSerializer, MenuRouteSerializer, MenuFormSerializer
)


@extend_schema(tags=["04.菜单接口"])
class MenuViewSet(BaseModelViewSet):
    """系统管理-菜单ViewSet。"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    queryset = Menu.objects.all().order_by('sort', 'id')
    filterset_class = MenuFilter

    def get_serializer_class(self):
        if self.action == 'create':
            return MenuCreateSerializer
        if self.action in ['update', 'partial_update']:
            return MenuUpdateSerializer
        if self.action == 'options':
            return MenuOptionSerializer
        if self.action == 'routes':
            return MenuRouteSerializer
        if self.action == 'form':
            return MenuFormSerializer
        return MenuSerializer

    @permission_required(["sys:menu:list"])
    @extend_schema(
        summary="菜单树形列表",
        parameters=[
            OpenApiParameter(
                name="keywords",
                location=OpenApiParameter.QUERY,
                required=False,
                type=str,
                description="关键词（菜单名称）",
            ),
            OpenApiParameter(
                name="status",
                location=OpenApiParameter.QUERY,
                required=False,
                type=int,
                description="菜单状态：1 启用 / 0 禁用",
            ),
        ],
        responses=resp("MenuTreeResult", MenuSerializer(many=True)),
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        keywords = request.query_params.get('keywords', '')
        if not keywords:
            queryset = queryset.filter(parent_id=0)

        status = request.query_params.get('status')
        visible = None
        if status is not None and status != "":
            try:
                visible = int(status)
            except ValueError:
                visible = None

        serializer = MenuSerializer(queryset.order_by('sort', 'id'), many=True, context={'visible': visible})
        return success(serializer.data, msg="获取菜单列表成功")

    @permission_required(["sys:menu:create"])
    @extend_schema(
        summary="新增菜单",
        request=MenuCreateSerializer,
        responses=resp("MenuCreateResult", MenuSerializer()),
    )
    def create(self, request, *args, **kwargs):
        serializer = MenuCreateSerializer(data=request.data)
        if serializer.is_valid():
            menu = serializer.save()
            response_serializer = MenuSerializer(menu)
            return success(response_serializer.data, msg="菜单创建成功")
        return error(serializer.errors)

    @permission_required(["sys:menu:update"])
    @extend_schema(
        summary="更新菜单",
        request=MenuUpdateSerializer,
        responses=resp("MenuUpdateResult", MenuSerializer()),
    )
    def update(self, request, *args, **kwargs):
        menu = self.get_object()
        serializer = MenuUpdateSerializer(menu, data=request.data, partial=True)
        if serializer.is_valid():
            updated_menu = serializer.save()
            response_serializer = MenuSerializer(updated_menu)
            return success(response_serializer.data, msg="菜单更新成功")
        return error(serializer.errors)

    @permission_required(["sys:menu:delete"])
    @extend_schema(
        summary="删除菜单",
        parameters=[
            OpenApiParameter(
                name="ids",
                location=OpenApiParameter.PATH,
                required=True,
                type=str,
                description="菜单ID，多个以英文逗号(,)分割",
            ),
        ],
        responses=resp("MenuDeleteResult", serializers.DictField(required=False)),
    )
    def destroy(self, request, *args, **kwargs):
        ids = kwargs.get(self.lookup_url_kwarg or self.lookup_field)

        if not ids:
            return error("请指定要删除的菜单ID")

        menu_ids = str(ids).split(',')
        try:
            menu_ids = [int(mid) for mid in menu_ids if mid]
        except ValueError:
            return error("菜单ID格式不正确")

        if not menu_ids:
            return error("请指定要删除的菜单ID")

        child_menus = Menu.objects.filter(parent_id__in=menu_ids)
        if child_menus.exists():
            return error("存在子菜单，无法删除")

        menus_to_delete = Menu.objects.filter(id__in=menu_ids)
        count = menus_to_delete.count()
        menus_to_delete.delete()
        return success({}, msg=f"成功删除{count}个菜单")

    @permission_required(["sys:menu:list"])
    @extend_schema(
        summary="菜单下拉选项",
        parameters=[
            OpenApiParameter(
                name="onlyParent",
                location=OpenApiParameter.QUERY,
                required=False,
                type=bool,
                description="是否仅返回父级菜单（true/false，默认 false）",
            ),
        ],
        responses=resp("MenuOptionsResult", MenuOptionSerializer(many=True)),
    )
    @action(methods=["get"], detail=False, url_path="options")
    def options(self, request, *args, **kwargs):
        only_parent = request.query_params.get('onlyParent', 'false').lower() == 'true'
        root_menus = Menu.objects.filter(parent_id=0).order_by('sort', 'id')
        if only_parent:
            root_menus = root_menus.exclude(type='B')
        context = {'only_parent': only_parent}
        serializer = MenuOptionSerializer(root_menus, many=True, context=context)
        return success(serializer.data)

    @extend_schema(
        summary="菜单路由",
        responses=resp("MenuRoutesResult", MenuRouteSerializer(many=True)),
    )
    @action(methods=["get"], detail=False, url_path="routes")
    def routes(self, request, *args, **kwargs):
        user_id = request.user.id
        role_ids = UserRole.objects.filter(user_id=user_id).values_list('role_id', flat=True)
        assigned_menu_ids = list(
            RoleMenu.objects.filter(role_id__in=role_ids).values_list('menu_id', flat=True).distinct()
        )

        include_ids = set()
        assigned_menus = Menu.objects.filter(id__in=assigned_menu_ids).exclude(type='B').only('id', 'parent_id', 'tree_path')
        for menu in assigned_menus:
            include_ids.add(menu.id)
            if menu.parent_id is not None:
                include_ids.add(menu.parent_id)
            if menu.tree_path:
                for pid in str(menu.tree_path).split(','):
                    pid = pid.strip()
                    if not pid:
                        continue
                    try:
                        include_ids.add(int(pid))
                    except ValueError:
                        continue

        root_menus = (
            Menu.objects.filter(Q(parent_id=0) & Q(id__in=include_ids))
            .exclude(type='B')
            .order_by('sort', 'id')
        )
        serializer = MenuRouteSerializer(root_menus, many=True, context={'menu_ids': list(include_ids)})
        return success(serializer.data, msg="获取菜单路由成功")

    @permission_required(["sys:menu:update"])
    @extend_schema(
        summary="菜单表单数据",
        responses=resp("MenuFormResult", MenuFormSerializer()),
    )
    @action(methods=["get"], detail=True, url_path="form")
    def form(self, request, pk=None, *args, **kwargs):
        menu = get_object_or_404(Menu, id=pk)
        serializer = MenuFormSerializer(menu)
        return success(serializer.data)
