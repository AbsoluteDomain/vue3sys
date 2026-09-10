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


class JwtRequiredMiddleware:
    """对 /api/v1/ 下的「写操作」强制 JWT 鉴权。

    背景：部分纯 Django 函数视图（@csrf_exempt，如出入库、关节绑定、BOM 装配）
    没有 DRF 认证层，access token 过期后业务仍会执行成功，导致仓库日志/操作日志
    写入 operator_name='系统' 且 operator_id=NULL 的脏数据，且无法追溯真实操作人。

    本中间件在请求进入视图前统一校验 access token 的签名与有效期：
      - 校验失败 → 直接返回 401 + A0230，前端拦截器收到后自动用 refresh token
        换新 access token 并重试原请求（对用户无感）；refresh 也失效则跳转登录页。
      - 校验通过 → 把 payload 挂到 request.META['_JWT_PAYLOAD']，供日志解析复用，
        避免重复解码，并保证写操作一定能拿到真实操作人。

    设计要点：
      - 只拦截写操作（POST/PUT/PATCH/DELETE）；GET/HEAD/OPTIONS 放行（不产生操作人记录）
      - 纯 JWT 签名 + exp 校验，不依赖 Redis（Redis 故障不影响车间作业）
      - tokenVersion/黑名单等强安全校验仍由 DRF 视图的 VersionedJWTAuthentication 负责
      - 认证白名单（登录/刷新/验证码/短信/微信登录/登出）直接放行
    """

    # 无需 access token 即可访问的路径前缀
    EXEMPT_PREFIXES = (
        "/api/v1/auth/login",             # 账号密码登录（含 /login/sms）
        "/api/v1/auth/sms/code",          # 发送短信验证码
        "/api/v1/auth/captcha",           # 图形验证码
        "/api/v1/auth/refresh-token",     # 刷新令牌（携带的是 refresh token）
        "/api/v1/auth/logout",            # 登出（旧 token 可能已失效）
        "/api/v1/auth/wechat/",           # 微信小程序登录/绑定
    )

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def _unauthorized(self, msg="登录状态已过期，请重新登录"):
        # code=A0230 + HTTP 401，与前端 request.ts 的自动刷新重试契约对齐
        return JsonResponse(
            {"code": "A0230", "msg": msg, "data": None},
            status=401,
        )

    def __call__(self, request):
        path = request.path or ""

        # 非业务 API、非写操作、CORS 预检：直接放行
        if (
            not path.startswith("/api/v1/")
            or request.method not in self.WRITE_METHODS
        ):
            return self.get_response(request)

        # 认证白名单放行
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # 提取 Bearer token
        auth_header = request.META.get("HTTP_AUTHORIZATION", "") or ""
        if not auth_header.startswith("Bearer "):
            return self._unauthorized("未检测到登录凭证，请先登录")
        raw_token = auth_header[7:].strip()
        if not raw_token:
            return self._unauthorized("未检测到登录凭证，请先登录")

        # 纯 JWT 校验（签名 + 过期时间），不依赖 Redis
        try:
            from rest_framework_simplejwt.backends import TokenBackend
            from django.conf import settings

            jwt_settings = getattr(settings, "SIMPLE_JWT", {})
            backend = TokenBackend(
                algorithm=jwt_settings.get("ALGORITHM", "HS256"),
                signing_key=jwt_settings.get("SIGNING_KEY", settings.SECRET_KEY),
            )
            payload = backend.decode(raw_token, verify=True)
        except Exception as exc:
            logger.info(
                "[JWT中间件] 写操作鉴权失败 path=%s method=%s err=%s",
                path, request.method, exc,
            )
            return self._unauthorized()

        # 必须是 access token 且带 user_id
        if payload.get("token_type") and payload.get("token_type") != "access":
            return self._unauthorized("登录凭证类型无效，请重新登录")
        if not payload.get("user_id"):
            return self._unauthorized("登录凭证无效，请重新登录")

        # 挂载解析结果，供 warehouse_logger / operation_logs 直接复用
        request.META["_JWT_PAYLOAD"] = payload

        return self.get_response(request)


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
    "JwtRequiredMiddleware",
    "RequestContextFilter",
    "RequestContextMiddleware",
    "request_id_var",
    "user_id_var",
    "path_var",
    "method_var",
    "status_var",
    "cost_ms_var",
]
