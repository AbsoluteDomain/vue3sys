from __future__ import annotations

from datetime import datetime, timedelta

import django_filters
from django.db.models import Q
from django.utils import timezone

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
        """创建时间范围筛选。

        兼容两种传参：
        1) 重复参数：`createTime=start&createTime=end`（前端日期范围组件的默认格式）
        2) 逗号分隔：`createTime=start,end`

        支持两种时间格式：
        - `YYYY-MM-DD HH:mm:ss`
        - `YYYY-MM-DD`（开始值按当天 00:00:00 处理，结束值按当天 23:59:59 处理，确保包含结束日全天）
        """
        data = getattr(self, "data", None)

        start_time, end_time = "", ""
        if data is not None:
            try:
                values = [v for v in data.getlist("createTime") if v]
            except Exception:
                values = []
            if len(values) >= 2:
                start_time, end_time = values[0], values[-1]
            elif len(values) == 1:
                parts = str(values[0]).split(",")
                if len(parts) == 2:
                    start_time, end_time = parts[0].strip(), parts[1].strip()

        if not (start_time or end_time):
            return queryset

        def _parse_bound(v, is_end):
            v = str(v).strip()
            if not v:
                return None
            try:
                return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
            try:
                day_start = datetime.strptime(v[:10], "%Y-%m-%d")
            except ValueError:
                return None
            if is_end:
                return day_start + timedelta(days=1) - timedelta(seconds=1)
            return day_start

        start_dt = _parse_bound(start_time, is_end=False) if start_time else None
        end_dt = _parse_bound(end_time, is_end=True) if end_time else None
        if start_dt is not None and start_dt.tzinfo is None:
            start_dt = timezone.make_aware(start_dt)
        if end_dt is not None and end_dt.tzinfo is None:
            end_dt = timezone.make_aware(end_dt)

        if start_dt is not None:
            queryset = queryset.filter(date_joined__gte=start_dt)
        if end_dt is not None:
            queryset = queryset.filter(date_joined__lte=end_dt)
        return queryset
