from __future__ import annotations

from typing import Any, Optional


class BusinessException(Exception):
    def __init__(
        self,
        msg: str,
        *,
        code: str = "B0001",
        status: int = 400,
        data: Any = None,
    ) -> None:
        super().__init__(msg)
        self.msg = msg
        self.code = code
        self.status = status
        self.data = data


def raise_if(condition: bool, msg: str, *, code: str = "B0001", status: int = 400, data: Any = None) -> None:
    if condition:
        raise BusinessException(msg, code=code, status=status, data=data)


def get_int(value: Any, *, default: Optional[int] = None, field: str = "") -> Optional[int]:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        raise BusinessException(f"{field or '参数'}格式不正确", code="A0400", status=400)
