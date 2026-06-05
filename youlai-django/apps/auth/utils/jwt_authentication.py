"""平台-认证模块。

"""

from django_redis import get_redis_connection
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class VersionedJWTAuthentication(JWTAuthentication):
    """扩展 SimpleJWT 的认证类，增加：
    - 用户 Token 版本号校验（auth:user:token_version:{user_id}）
    - Token 黑名单校验（auth:token:blacklist:{jti}）
    """

    def get_validated_token(self, raw_token):
        # 先由父类完成签名和过期时间等基础校验
        validated_token = super().get_validated_token(raw_token)

        redis_conn = get_redis_connection("default")

        # 1. 校验用户 Token 版本号
        user_id = validated_token.get("user_id")
        token_version = validated_token.get("tokenVersion", 0)

        if user_id is not None:
            version_key = f"auth:user:token_version:{user_id}"
            current_version = redis_conn.get(version_key)
            current_version_int = int(current_version) if current_version is not None else 0

            if token_version < current_version_int:
                raise AuthenticationFailed("访问令牌已失效，请重新登录", code="token_invalidated")

        # 2. 校验黑名单
        jti = validated_token.get("jti")
        if jti is not None:
            blacklist_key = f"auth:token:blacklist:{jti}"
            if redis_conn.exists(blacklist_key):
                raise AuthenticationFailed("访问令牌已失效，请重新登录", code="token_blacklisted")

        return validated_token
