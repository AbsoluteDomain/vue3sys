"""平台-认证模块。

"""

from django.conf import settings
from django_redis import get_redis_connection


def invalidate_user_sessions(user_id: int) -> None:
    """失效指定用户的所有会话

    - JWT 模式：递增 auth:user:token_version:{userId}
    - redis-token 模式：删除该用户的 access/refresh 映射
    """
    if not user_id:
        return

    redis_conn = get_redis_connection("default")
    session_type = getattr(settings, "SESSION_TYPE", "jwt")

    # 1. JWT 模式：递增 Token 版本号
    version_key = f"auth:user:token_version:{user_id}"
    try:
        redis_conn.incr(version_key)
    except Exception:
        # 出错时不影响主流程
        pass

    # 2. redis-token 模式：清理 access/refresh 映射
    if session_type == "redis-token":
        access_key = f"auth:user:access:{user_id}"
        refresh_key = f"auth:user:refresh:{user_id}"

        access_token = redis_conn.get(access_key)
        refresh_token = redis_conn.get(refresh_key)

        if access_token:
            redis_conn.delete(f"auth:token:access:{access_token.decode('utf-8')}")
        if refresh_token:
            redis_conn.delete(f"auth:token:refresh:{refresh_token.decode('utf-8')}")

        redis_conn.delete(access_key)
        redis_conn.delete(refresh_key)
