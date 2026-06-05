"""handler 模块。

"""

import logging
from typing import Any

from django.http import Http404
from django.db.utils import OperationalError, ProgrammingError, IntegrityError
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler

from core.exceptions.business import BusinessException
from core.response import error

logger = logging.getLogger(__name__)


"""DRF 全局异常处理。

将 DRF 原生异常统一转换为项目标准错误响应结构，并保证异常信息可读、可追踪。
"""


def _stringify_error_detail(detail: Any) -> str:
    """把 DRF 的 error detail（可能是 str/list/dict）规整成单个可读字符串。"""
    if detail is None:
        return ""

    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        return "；".join(filter(None, [_stringify_error_detail(x) for x in detail]))

    if isinstance(detail, dict):
        if "msg" in detail and isinstance(detail.get("msg"), str):
            return detail["msg"]
        parts: list[str] = []
        for k, v in detail.items():
            v_str = _stringify_error_detail(v)
            if not v_str:
                continue
            parts.append(f"{k}: {v_str}")
        return "；".join(parts)

    return str(detail)


def global_exception_handler(exc: Exception, context: dict) -> Any:
    """DRF `EXCEPTION_HANDLER` 入口。"""
    if isinstance(exc, BusinessException):
        return error(exc.msg, code=exc.code, status=exc.status, data=exc.data)

    resp = drf_exception_handler(exc, context)

    if resp is None:
        request = context.get("request")
        method = getattr(request, "method", "") if request is not None else ""

        if method and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            err_str = str(exc)
            demo_markers = (
                "read-only",
                "read only",
                "readonly",
                "command denied",
                "access denied",
                "permission denied",
                "denied",
            )
            if isinstance(exc, (OperationalError, ProgrammingError, IntegrityError)) and any(
                marker in err_str.lower() for marker in demo_markers
            ):
                return error(
                    "演示系统，请本地部署后关闭演示功能使用",
                    code="A0402",
                    status=403,
                )

        if isinstance(exc, (OperationalError, ProgrammingError)):
            err_str = str(exc)
            if "Unknown column" in err_str or "unknown column" in err_str:
                logger.exception("Database schema mismatch detected (Unknown column)", exc_info=exc)
                return error(
                    "数据库表结构与后端模型不一致，请重新导入 sql/mysql/youlai_admin_django.sql，或执行 python manage.py migrate 同步表结构",
                    status=500,
                )
        logger.exception("Unhandled exception", exc_info=exc)
        return error("系统执行出错", status=500)

    status_code = getattr(resp, "status_code", 500)
    detail = getattr(resp, "data", None)

    if isinstance(exc, ValidationError):
        if isinstance(detail, dict) and "code" in detail and "msg" in detail:
            # 刷新令牌无效返回 401，与 Java 后端保持一致
            code_value = detail.get("code")
            status = 401 if code_value == "A0231" else status_code
            return error(detail.get("msg"), code=code_value, status=status)
        msg = _stringify_error_detail(detail) or "用户请求参数错误"
        return error(msg, status=status_code)

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        msg = _stringify_error_detail(detail) or "访问未授权"
        if msg in {
            "Not authenticated",
            "Authentication credentials were not provided.",
            "Authentication credentials were not provided",
        }:
            msg = "未认证，请先登录"
        if msg in {"Invalid token.", "Invalid token", "Token is invalid or expired"}:
            msg = "无效的访问令牌"
        return error(msg, status=401)

    if isinstance(exc, PermissionDenied):
        msg = _stringify_error_detail(detail) or "权限不足"
        if msg in {"Permission denied", "Permission denied."}:
            msg = "权限不足"
        return error(msg, status=403)

    if isinstance(exc, Http404):
        msg = _stringify_error_detail(detail) or "接口不存在"
        return error(msg, status=404)

    if isinstance(exc, Throttled):
        msg = _stringify_error_detail(detail) or "请求次数超出限制"
        return error(msg, status=429)

    if isinstance(exc, APIException):
        msg = _stringify_error_detail(detail) or "请求处理失败"
        return error(msg, status=status_code)

    msg = _stringify_error_detail(detail) or str(exc) or "请求处理失败"
    return error(msg, status=status_code)
