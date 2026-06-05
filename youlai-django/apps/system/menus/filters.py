from __future__ import annotations

import django_filters
from django.db.models import Q

from apps.system.menus.models import Menu


class MenuFilter(django_filters.FilterSet):
    """菜单树筛选器。

    这里的列表接口返回的是“树形结构”。

    - `keywords`：按菜单名称模糊搜。为了让树能展开，会把匹配节点的祖先链路也一并捞出来。
    - `status`：菜单显示状态，对应模型字段 `visible`（1 显示 / 0 隐藏）。

    说明：
    - 筛选器只负责把“该展示的菜单范围”圈出来；
    - 具体怎么拼成树（递归 children），还是由 Serializer 做。
    """

    keywords = django_filters.CharFilter(method="filter_keywords")
    status = django_filters.CharFilter(method="filter_visible")

    class Meta:
        model = Menu
        fields: list[str] = []

    def filter_keywords(self, queryset, name, value):
        if not value:
            return queryset

        matching = Menu.objects.filter(name__icontains=value).only("id", "tree_path", "parent_id")
        if not matching.exists():
            return queryset.none()

        include_ids: set[int] = set()
        for menu in matching:
            include_ids.add(int(menu.id))
            if menu.parent_id is not None:
                try:
                    include_ids.add(int(menu.parent_id))
                except (TypeError, ValueError):
                    pass
            if menu.tree_path:
                for pid in str(menu.tree_path).split(","):
                    pid = pid.strip()
                    if not pid:
                        continue
                    try:
                        include_ids.add(int(pid))
                    except (TypeError, ValueError):
                        continue

        return queryset.filter(Q(id__in=include_ids) | Q(parent_id__in=include_ids))

    def filter_visible(self, queryset, name, value):
        if value is None or value == "":
            return queryset
        try:
            visible = int(value)
        except (TypeError, ValueError):
            return queryset
        return queryset.filter(visible=visible)
