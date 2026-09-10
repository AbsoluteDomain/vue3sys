"""datetime 模块。

项目约定：单一时区（TIME_ZONE = Asia/Shanghai）、纯内网部署，
因此关闭 Django 时区支持（USE_TZ=False），数据库直接存储北京时间字面值，
数据库工具 / 页面 / Excel 导出看到的时间完全一致。

本模块的工具函数同时兼容 USE_TZ=True/False 两种模式，保证切换期与
历史代码的安全：返回值的 aware/naive 属性始终与当前 USE_TZ 设置一致，
避免查询时 naive/aware 混用报错。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

from django.conf import settings
from django.utils import timezone as dj_timezone

LOCAL_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
LOCAL_DATE_FMT = "%Y-%m-%d"


def utc_now() -> datetime:
    """UTC 当前时间（aware）。仅用于与 Django 配置无关的 UTC 场景。"""
    return datetime.now(tz=timezone.utc)


def parse_local_datetime_text(value) -> Optional[datetime]:
    """解析 `YYYY-MM-DD HH:MM:SS` 或 `YYYY-MM-DD` 格式的本地时间文本。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text[:19], LOCAL_DATETIME_FMT)
    except ValueError:
        try:
            return datetime.strptime(text[:10], LOCAL_DATE_FMT)
        except ValueError:
            return None


def to_local_naive(value: datetime) -> datetime:
    """统一转为本地时区（Asia/Shanghai）的 naive datetime。

    - naive 值：视为本地时间，原样返回；
    - aware 值：先转到当前配置时区，再去掉 tzinfo。
    """
    if value is None:
        return None
    if dj_timezone.is_aware(value):
        value = dj_timezone.localtime(value)
        return value.replace(tzinfo=None)
    return value


def make_local_aware(value: datetime) -> datetime:
    """把输入的本地时间 datetime 转为与 USE_TZ 配置一致的形态。

    - USE_TZ=True：返回带 Asia/Shanghai tzinfo 的 aware datetime；
    - USE_TZ=False：返回 naive datetime（数据库即存本地墙钟时间）；
    - 输入已经是 aware 时，先归一到本地时区再按配置决定是否保留 tzinfo。
    """
    if value is None:
        return None
    local_naive = to_local_naive(value)
    if getattr(settings, "USE_TZ", False):
        return dj_timezone.make_aware(local_naive, dj_timezone.get_current_timezone())
    return local_naive


def local_date_key(value) -> Optional[str]:
    """按本地时间提取日期键 YYYY-MM-DD。"""
    if not value:
        return None
    if isinstance(value, datetime):
        return to_local_naive(value).strftime(LOCAL_DATE_FMT)
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 10:
            return text[:10]
    parsed = parse_local_datetime_text(value)
    if parsed:
        return parsed.strftime(LOCAL_DATE_FMT)
    return None


def local_day_range_datetimes(start_day: date, end_day: date) -> Tuple[datetime, datetime]:
    """返回本地时区下某日期范围的起止时间（含首尾日全天）。

    USE_TZ=True 时返回 aware，USE_TZ=False 时返回 naive，
    可直接用于 ORM 的 gte/lte 范围过滤。
    """
    start_dt = make_local_aware(datetime.combine(start_day, time.min))
    end_dt = make_local_aware(datetime.combine(end_day, time(23, 59, 59)))
    return start_dt, end_dt


def format_local_datetime(value, fmt: str = LOCAL_DATETIME_FMT) -> Optional[str]:
    """将 datetime 格式化为本地时间（Asia/Shanghai）字符串。

    无论 USE_TZ 开关、输入是 aware 还是 naive，输出都是北京时间字面值。
    """
    if not value:
        return None
    return to_local_naive(value).strftime(fmt)
