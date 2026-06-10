"""datetime 模块。

"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

from django.utils import timezone as dj_timezone

LOCAL_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
LOCAL_DATE_FMT = "%Y-%m-%d"


def utc_now() -> datetime:
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


def make_local_aware(value: datetime) -> datetime:
    """将 naive datetime 视为当前配置时区（默认 Asia/Shanghai）的本地时间。"""
    if dj_timezone.is_aware(value):
        return value
    return dj_timezone.make_aware(value, dj_timezone.get_current_timezone())


def local_date_key(value) -> Optional[str]:
    """按 `YYYY-MM-DD HH:MM:SS` 本地时间提取日期键 YYYY-MM-DD。"""
    if not value:
        return None
    if isinstance(value, datetime):
        if dj_timezone.is_naive(value):
            return value.strftime(LOCAL_DATE_FMT)
        return dj_timezone.localtime(value).strftime(LOCAL_DATE_FMT)
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 10:
            return text[:10]
    parsed = parse_local_datetime_text(value)
    if parsed:
        return parsed.strftime(LOCAL_DATE_FMT)
    return None


def local_day_range_datetimes(start_day: date, end_day: date) -> Tuple[datetime, datetime]:
    """返回本地时区下某日期范围的起止时间（含首尾日全天）。"""
    start_dt = make_local_aware(datetime.combine(start_day, time.min))
    end_dt = make_local_aware(datetime.combine(end_day, time(23, 59, 59)))
    return start_dt, end_dt


def format_local_datetime(value, fmt: str = LOCAL_DATETIME_FMT) -> Optional[str]:
    """将 datetime 格式化为当前配置时区（默认 Asia/Shanghai）的本地时间字符串。"""
    if not value:
        return None
    if dj_timezone.is_naive(value):
        value = dj_timezone.make_aware(value, dj_timezone.get_current_timezone())
    return dj_timezone.localtime(value).strftime(fmt)
