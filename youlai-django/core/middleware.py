"""middleware 模块。

请求上下文中间件。
"""

import logging
import time
import uuid
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")
path_var: ContextVar[str] = ContextVar("path", default="-")
method_var: ContextVar[str] = ContextVar("method", default="-")
status_var: ContextVar[str] = ContextVar("status", default="-")
cost_ms_var: ContextVar[str] = ContextVar("cost_ms", default="-")


class RequestContextFilter(logging.Filter):
    """日志过滤器，注入请求上下文信息。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.path = path_var.get()
        record.method = method_var.get()
        record.status = status_var.get()
        record.cost_ms = cost_ms_var.get()
        return True


class RequestContextMiddleware:
    """请求上下文中间件。

    每个请求进来时生成 request_id，并把路径、方法、耗时、用户信息塞进上下文，
    后面的日志就能带上这些字段，排查问题会清楚很多。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()

        rid_token = request_id_var.set(uuid.uuid4().hex[:16])
        path_token = path_var.set(getattr(request, "path", "-") or "-")
        method_token = method_var.set(getattr(request, "method", "-") or "-")
        status_token = status_var.set("-")
        cost_token = cost_ms_var.set("-")
        user_token = user_id_var.set("-")

        try:
            response = self.get_response(request)

            try:
                response["X-Request-Id"] = request_id_var.get()
            except Exception:
                pass

            return response
        finally:
            try:
                cost_ms = int((time.time() - start) * 1000)
            except Exception:
                cost_ms = -1

            status = None
            try:
                status = str(getattr(locals().get("response", None), "status_code", "-"))
            except Exception:
                status = "-"

            status_var.set(status)
            cost_ms_var.set(str(cost_ms))

            uid = "-"
            try:
                user = getattr(request, "user", None)
                if user is not None and getattr(user, "is_authenticated", False):
                    uid = str(getattr(user, "id", "-"))
            except Exception:
                uid = "-"
            user_id_var.set(uid)

            logger.info("request")

            try:
                if "response" in locals() and locals()["response"] is not None:
                    locals()["response"]["X-Request-Id"] = request_id_var.get()
            except Exception:
                pass

            request_id_var.reset(rid_token)
            path_var.reset(path_token)
            method_var.reset(method_token)
            status_var.reset(status_token)
            cost_ms_var.reset(cost_token)
            user_id_var.reset(user_token)


__all__ = [
    "RequestContextFilter",
    "RequestContextMiddleware",
    "request_id_var",
    "user_id_var",
    "path_var",
    "method_var",
    "status_var",
    "cost_ms_var",
]
