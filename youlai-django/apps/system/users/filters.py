from __future__ import annotations

import django_filters
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from apps.system.users.models import User


class UserFilter(django_filters.FilterSet):
    """用户列表筛选器（django-filter）。

    说明：
    - 该筛选器仅负责“条件筛选”（keywords/status/deptId/roleIds/createTime）。
    - 数据权限（可见用户范围）应在 ViewSet 的 `get_queryset()` 中处理。

    参数约定：
    - `keywords`：用户名/昵称/手机号 模糊匹配。
    - `status`：用户状态。
    - `deptId`：部门ID。
    - `roleIds`：角色ID列表，多个以英文逗号(,)分割。
    - `createTime`：创建时间范围，格式 `start,end`（可被 `parse_datetime` 解析）。
    """

    keywords = django_filters.CharFilter(method="filter_keywords")
    status = django_filters.CharFilter(method="filter_status")
    deptId = django_filters.CharFilter(method="filter_dept")
    roleIds = django_filters.CharFilter(method="filter_roles")
    createTime = django_filters.CharFilter(method="filter_create_time")

    class Meta:
        model = User
        fields: list[str] = []

    def filter_keywords(self, queryset, name, value):
        """关键词：用户名/昵称/手机号。"""
        if not value:
            return queryset
        return queryset.filter(
            Q(username__icontains=value)
            | Q(nickname__icontains=value)
            | Q(mobile__icontains=value)
        )

    def filter_status(self, queryset, name, value):
        """状态：1 启用 / 0 禁用。"""
        if value is None or value == "":
            return queryset
        try:
            return queryset.filter(status=int(value))
        except (TypeError, ValueError):
            return queryset

    def filter_dept(self, queryset, name, value):
        """部门ID筛选。"""
        if not value:
            return queryset
        return queryset.filter(dept_id=value)

    def filter_roles(self, queryset, name, value):
        """角色ID筛选（逗号分隔）。"""
        if not value:
            return queryset
        role_id_list = str(value).split(",")
        role_id_list = [v for v in role_id_list if v]
        if not role_id_list:
            return queryset
        return queryset.filter(roles__id__in=role_id_list)

    def filter_create_time(self, queryset, name, value):
        """创建时间范围：`start,end`，使用 `parse_datetime` 解析。"""
        if not value:
            return queryset
        parts = str(value).split(",")
        if len(parts) != 2:
            return queryset
        start_time, end_time = parts[0].strip(), parts[1].strip()
        start_dt = parse_datetime(start_time) if start_time else None
        end_dt = parse_datetime(end_time) if end_time else None

        # 结束日期拼接 23:59:59，包含当天所有数据
        if end_dt is None and end_time and len(end_time) == 10:
            from datetime import datetime, time
            try:
                end_dt = datetime.combine(datetime.strptime(end_time, "%Y-%m-%d").date(), time(23, 59, 59))
            except ValueError:
                pass

        if start_dt and end_dt:
            return queryset.filter(date_joined__gte=start_dt, date_joined__lte=end_dt)
        return queryset
