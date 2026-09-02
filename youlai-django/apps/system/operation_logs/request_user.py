import importlib
import logging

from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """获取客户端 IP"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _extract_bearer_token(request):
    """从请求里抽出 Bearer token，拿不到返回空串。"""
    auth_header = request.META.get("HTTP_AUTHORIZATION") or ""
    if not auth_header and hasattr(request, "headers"):
        auth_header = request.headers.get("Authorization") or ""
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return ""


def _jwt_fallback_resolve(token):
    """纯 JWT 签名解码（不依赖 Redis / 不跑 VersionedJWTAuthentication 那套逻辑）。

    Function-based view（@csrf_exempt/@require_http_methods）不走 DRF 的认证流程，
    靠 VersionedJWTAuthentication.authenticate(request) 时，内部会访问 Redis 查
    tokenVersion/blacklist。一旦 Redis 慢或连不上，authenticate 会 catch 后直接
    返回原 token，再走 DRF 的 get_user() 流程——这些在 Django 纯函数视图里都不稳定。

    直接用 TokenBackend.decode 拿 user_id 是 O(1) 且不依赖外部服务，用来解析操作日志
    的用户名绰绰有余（操作日志是「谁做了什么」记录，不需要 tokenVersion 强校验，
    JWT 本身未过期未篡改就可信）。
    """
    if not token:
        return None
    try:
        from rest_framework_simplejwt.backends import TokenBackend

        jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        token_backend = TokenBackend(
            algorithm=jwt_settings.get("ALGORITHM", "HS256"),
            signing_key=jwt_settings.get("SIGNING_KEY", settings.SECRET_KEY),
        )
        token_data = token_backend.decode(token, verify=True)
        user_id = token_data.get("user_id")
        if not user_id:
            return None
    except Exception as exc:
        logger.debug("JWT fallback 解析失败: %s", exc)
        return None

    User = get_user_model()
    db_user = (
        User.objects.filter(id=user_id)
        .only("id", "username", "nickname")
        .first()
    )
    if not db_user:
        return None
    username = db_user.username or db_user.nickname
    if not username:
        return None
    return db_user.id, username


def get_request_operator(request):
    """从请求中解析当前操作用户，返回 (user_id, user_name) 或 None。

    解析优先级：
      1. 纯 JWT fallback —— 不依赖 Redis，对纯函数视图最稳，先走这一步。
      2. 遍历 DRF DEFAULT_AUTHENTICATION_CLASSES（正常 APIView 会命中）。
      3. request.user（常规 Django session / middleware 场景）。
    """
    User = get_user_model()

    # --- 1. JWT fallback（不依赖 Redis，稳定性最高） ---
    operator = _jwt_fallback_resolve(_extract_bearer_token(request))
    if operator:
        return operator

    # --- 2. DRF 认证类兜底 ---
    auth_class_paths = getattr(settings, "REST_FRAMEWORK", {}).get(
        "DEFAULT_AUTHENTICATION_CLASSES", ()
    )
    drf_errors = []
    for auth_class_path in auth_class_paths:
        try:
            module_path, class_name = auth_class_path.rsplit(".", 1)
            auth_module = importlib.import_module(module_path)
            auth_instance = getattr(auth_module, class_name)()
            result = auth_instance.authenticate(request)
            if result is None:
                continue
            user, _token = result
            if user is not None:
                username = getattr(user, "username", None) or getattr(user, "nickname", None)
                if user.id and username:
                    return user.id, username

            user_session = getattr(request, "user_session", None)
            if user_session and user_session.user_id:
                username = user_session.username or str(user_session.user_id)
                return user_session.user_id, username
        except Exception as exc:
            drf_errors.append(f"{auth_class_path}: {exc}")

    if drf_errors:
        logger.debug(
            "DRF 认证类解析操作用户失败 path=%s errors=%s",
            getattr(request, "path", ""),
            " | ".join(drf_errors),
        )

    # --- 3. request.user 兜底（Django 会话 / 中间件） ---
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        username = getattr(user, "username", None) or getattr(user, "nickname", None)
        if user.id and username:
            return user.id, username

    return None
