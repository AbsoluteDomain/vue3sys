from __future__ import annotations

from datetime import datetime, timedelta
import logging

import django_filters
from django.db.models import Q
from django.utils import timezone

from apps.system.logs.models import Log


_logger = logging.getLogger(__name__)


class LogFilter(django_filters.FilterSet):
    """日志筛选器（django-filter）。

    - **keywords**：关键词（多字段模糊匹配）。
    - **createTime**：创建时间范围（兼容多种前端传参方式）。
    """

    keywords = django_filters.CharFilter(method="filter_keywords")
    createTime = django_filters.CharFilter(method="filter_create_time")

    class Meta:
        model = Log
        fields: list[str] = []

    def filter_keywords(self, queryset, name, value):
        """关键词筛选。

        说明：对日志内容/请求路径/请求方式/省市/浏览器/系统等字段做 `icontains` 模糊匹配。
        """
        if not value:
            return queryset
        _logger.debug("logs filter keywords name=%s value=%s", name, value)
        return queryset.filter(
            Q(content__icontains=value)
            | Q(request_uri__icontains=value)
            | Q(method__icontains=value)
            | Q(province__icontains=value)
            | Q(city__icontains=value)
            | Q(browser__icontains=value)
            | Q(os__icontains=value)
        )

    def filter_create_time(self, queryset, name, value):
        """创建时间范围筛选。

        兼容以下两种传参：

        1) 重复参数（SpringBoot 常见写法）
           - `createTime=2026-02-13&createTime=2026-02-14`

        2) 逗号分隔
           - `createTime=2026-02-13 00:00:00,2026-02-14 23:59:59`

        时间格式支持：
        - `YYYY-MM-DD HH:mm:ss`
        - `YYYY-MM-DD`（结束日期会按当天 23:59:59 处理，确保“包含结束日”）

        时区处理：
        - 项目开启 `USE_TZ=True`，这里会将 naive datetime 转为 aware datetime。
        """
        data = getattr(self, "data", None)
        if data is None:
            return queryset

        create_time_list = []
        try:
            create_time_list = data.getlist("createTime")
        except Exception:
            create_time_list = []

        _logger.debug(
            "logs filter createTime name=%s value=%s create_time_list=%s",
            name,
            value,
            create_time_list,
        )

        start_time = ""
        end_time = ""

        if len(create_time_list) >= 2:
            start_time, end_time = create_time_list[0], create_time_list[1]
        elif value:
            parts = str(value).split(",")
            if len(parts) == 2:
                start_time, end_time = parts

        if not (start_time or end_time):
            return queryset

        _logger.debug("logs filter createTime resolved start=%s end=%s", start_time, end_time)

        def _parse_start(v: str):
            try:
                return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.strptime(v, "%Y-%m-%d")

        def _parse_end(v: str):
            try:
                return datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.strptime(v, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)

        if start_time:
            try:
                start_dt = _parse_start(str(start_time))
                if start_dt.tzinfo is None:
                    start_dt = timezone.make_aware(start_dt)
                _logger.debug("logs filter createTime parsed start_dt=%s", start_dt)
                queryset = queryset.filter(create_time__gte=start_dt)
            except ValueError:
                _logger.warning("logs filter createTime invalid start_time=%s", start_time)
                pass

        if end_time:
            try:
                end_dt = _parse_end(str(end_time))
                if end_dt.tzinfo is None:
                    end_dt = timezone.make_aware(end_dt)
                _logger.debug("logs filter createTime parsed end_dt=%s", end_dt)
                queryset = queryset.filter(create_time__lte=end_dt)
            except ValueError:
                _logger.warning("logs filter createTime invalid end_time=%s", end_time)
                pass

        return queryset
