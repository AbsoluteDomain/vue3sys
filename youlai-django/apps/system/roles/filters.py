from __future__ import annotations

import django_filters
from django.db.models import Q
from django.utils.dateparse import parse_datetime

from apps.system.roles.models import Role


class RoleFilter(django_filters.FilterSet):
    """角色列表筛选器。

    目前前端查询参数沿用既有约定：
    - `keywords`：角色名称/角色编码 模糊匹配
    - `startDate`、`endDate`：创建时间范围（可被 `parse_datetime` 解析）

    说明：数据权限（按创建人过滤）在 ViewSet 的 `get_queryset()` 里处理。
    """

    keywords = django_filters.CharFilter(method="filter_keywords")
    startDate = django_filters.CharFilter(method="filter_date_range")
    endDate = django_filters.CharFilter(method="filter_date_range")

    class Meta:
        model = Role
        fields: list[str] = []

    def filter_keywords(self, queryset, name, value):
        """关键词：角色名/角色编码。"""
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(code__icontains=value))

    def filter_date_range(self, queryset, name, value):
        """创建时间范围筛选。

        这里同时读取 `startDate/endDate` 两个参数；只有两者都合法时才应用过滤。
        """
        data = getattr(self, "data", None)
        if data is None:
            return queryset

        start_date = data.get("startDate")
        end_date = data.get("endDate")
        if not (start_date and end_date):
            return queryset

        start_dt = parse_datetime(str(start_date))
        end_dt = parse_datetime(str(end_date))
        if not (start_dt and end_dt):
            return queryset

        return queryset.filter(create_time__gte=start_dt, create_time__lte=end_dt)
