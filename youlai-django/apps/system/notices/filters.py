from __future__ import annotations

import django_filters
from django.utils.dateparse import parse_datetime

from apps.system.notices.models import Notice


class NoticeFilter(django_filters.FilterSet):
    """通知公告列表筛选器。

    参数约定（沿用现有接口文档）：
    - `title`：标题关键字（模糊匹配）
    - `publishStatus`：发布状态（0/1/-1）
    - `publishTime`：发布时间范围，格式 `start,end`（可被 `parse_datetime` 解析）

    说明：数据权限（按 create_by 过滤）在 ViewSet 的 `get_queryset()` 中处理。
    """

    title = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    publishStatus = django_filters.NumberFilter(field_name="publish_status")
    publishTime = django_filters.CharFilter(method="filter_publish_time")

    class Meta:
        model = Notice
        fields: list[str] = []

    def filter_publish_time(self, queryset, name, value):
        """发布时间范围：`start,end`。"""
        if not value:
            return queryset
        parts = str(value).split(",")
        if len(parts) != 2:
            return queryset
        start_time, end_time = parts[0], parts[1]
        start_dt = parse_datetime(start_time) if start_time else None
        end_dt = parse_datetime(end_time) if end_time else None
        if start_dt and end_dt:
            return queryset.filter(publish_time__gte=start_dt, publish_time__lte=end_dt)
        return queryset
