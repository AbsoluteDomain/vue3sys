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


def get_request_operator(request):
    """从请求中解析当前操作用户，返回 (user_id, user_name) 或 None。"""
    User = get_user_model()

    auth_class_paths = getattr(settings, "REST_FRAMEWORK", {}).get(
        "DEFAULT_AUTHENTICATION_CLASSES", ()
    )
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
            logger.debug("解析操作用户失败(%s): %s", auth_class_path, exc)

    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        username = getattr(user, "username", None) or getattr(user, "nickname", None)
        if user.id and username:
            return user.id, username

    auth_header = request.META.get("HTTP_AUTHORIZATION") or ""
    if not auth_header and hasattr(request, "headers"):
        auth_header = request.headers.get("Authorization") or ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            try:
                from rest_framework_simplejwt.backends import TokenBackend

                jwt_settings = getattr(settings, "SIMPLE_JWT", {})
                token_backend = TokenBackend(
                    algorithm=jwt_settings.get("ALGORITHM", "HS256"),
                    signing_key=jwt_settings.get("SIGNING_KEY", settings.SECRET_KEY),
                )
                token_data = token_backend.decode(token, verify=True)
                user_id = token_data.get("user_id")
                if user_id:
                    db_user = (
                        User.objects.filter(id=user_id)
                        .only("id", "username", "nickname")
                        .first()
                    )
                    if db_user:
                        username = db_user.username or db_user.nickname
                        if username:
                            return db_user.id, username
            except Exception as exc:
                logger.debug("JWT fallback 解析操作用户失败: %s", exc)

    return None
