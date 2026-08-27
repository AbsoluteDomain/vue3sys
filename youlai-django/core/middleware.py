"""middleware 模块。

请求上下文中间件。
"""

import logging
import time
import uuid
from contextvars import ContextVar

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# 上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var: ContextVar[str] = ContextVar("user_id", default="-")
path_var: ContextVar[str] = ContextVar("path", default="-")
method_var: ContextVar[str] = ContextVar("method", default="-")
status_var: ContextVar[str] = ContextVar("status", default="-")
cost_ms_var: ContextVar[str] = ContextVar("cost_ms", default="-")


class CorsMiddleware:
    """轻量 CORS 中间件，开发/生产都能用。

    让前端开发环境可直接直连 Django（绕过 vite proxy 的性能瓶颈），
    也让生产环境部署更灵活。
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # CORS 预检请求（OPTIONS）：直接返回 200，不走 Django 后续中间件链
        # 避免 CSRF / 认证中间件把 OPTIONS 拦掉导致浏览器 CORS 失败
        if request.method == "OPTIONS":
            response = JsonResponse({"code": "00000", "msg": "preflight ok"})
        else:
            response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-Id"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
        response["Access-Control-Max-Age"] = "3600"
        return response

    def process_exception(self, request, exception):
        # 即使抛异常也加 CORS 头
        response = JsonResponse({"code": "500", "msg": str(exception)}, status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response


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
