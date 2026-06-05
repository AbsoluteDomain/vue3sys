"""环境变量加载工具。

这个模块专门用来读取项目根目录下的 .env 文件，把里面的配置项加载到环境变量里。
它提供了一系列工具函数（比如 `env.bool`, `env.str`），方便在 `settings.py`
里安全地获取各种类型的配置，同时还能设置默认值。

"""

from __future__ import annotations

import os
from typing import Optional


_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


def _get_env(key: str) -> Optional[str]:
    value = os.getenv(key)
    if value is None:
        return None
    return value.strip()


def require_env(key: str) -> str:
    value = _get_env(key)
    if not value:
        raise RuntimeError(f"{key} is required")
    return value


def env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    value = _get_env(key)
    if value:
        return value
    return default


def env_int(key: str, default: Optional[int] = None) -> Optional[int]:
    value = _get_env(key)
    if value:
        return int(value)
    return default


def env_float(key: str, default: Optional[float] = None) -> Optional[float]:
    value = _get_env(key)
    if value:
        return float(value)
    return default


def env_bool(key: str, default: bool = False) -> bool:
    value = _get_env(key)
    if value is None or value == "":
        return default
    lowered = value.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean for {key}: {value}")
