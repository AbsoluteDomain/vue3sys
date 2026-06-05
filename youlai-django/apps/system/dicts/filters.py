from __future__ import annotations

import django_filters
from django.db.models import Q

from apps.system.dicts.models import Dictionary, DictionaryItem


class DictFilter(django_filters.FilterSet):
    """字典列表筛选器。

    - `keywords`：字典名称/字典编码 模糊匹配。

    说明：数据权限（按 create_by 过滤）在 ViewSet 的 `get_queryset()` 中处理。
    """

    keywords = django_filters.CharFilter(method="filter_keywords")

    class Meta:
        model = Dictionary
        fields: list[str] = []

    def filter_keywords(self, queryset, name, value):
        """关键字：字典名称/字典编码。"""
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(dict_code__icontains=value))


class DictItemFilter(django_filters.FilterSet):
    """字典项列表筛选器。

    - `keywords`：字典项 value/label 模糊匹配。

    说明：
    - dict_code 由路由参数控制（ViewSet.get_queryset）。
    - 数据权限（按 create_by 过滤）在 View 内处理（保持原有返回结构）。
    """

    keywords = django_filters.CharFilter(method="filter_keywords")

    class Meta:
        model = DictionaryItem
        fields: list[str] = []

    def filter_keywords(self, queryset, name, value):
        """关键字：value/label。"""
        if not value:
            return queryset
        return queryset.filter(Q(value__icontains=value) | Q(label__icontains=value))
