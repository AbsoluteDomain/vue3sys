from __future__ import annotations

import django_filters

from apps.system.configs.models import SysConfig


class ConfigFilter(django_filters.FilterSet):
    """系统配置列表筛选器。

    - `configName`：配置名称关键字（icontains）
    - `configKey`：配置 Key 关键字（icontains）

    说明：
    - 这里只做条件筛选；分页/排序由 DRF 处理。
    """

    configName = django_filters.CharFilter(field_name="config_name", lookup_expr="icontains")
    configKey = django_filters.CharFilter(field_name="config_key", lookup_expr="icontains")

    class Meta:
        model = SysConfig
        fields: list[str] = []
