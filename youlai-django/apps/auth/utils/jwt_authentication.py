"""平台-认证模块。

"""

import logging

from django_redis import get_redis_connection
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class VersionedJWTAuthentication(JWTAuthentication):
    """扩展 SimpleJWT 的认证类，增加：
    - 用户 Token 版本号校验（auth:user:token_version:{user_id}）
    - Token 黑名单校验（auth:token:blacklist:{jti}）

    注意：Token 版本号和黑名单校验依赖 Redis。若 Redis 不可用，
    跳过这两步校验，退化为纯 JWT 签名校验，不阻塞请求。
    这意味着 Redis 异常期间，强制下线（递增 tokenVersion）会暂时失效。
    """

    def get_validated_token(self, raw_token):
        # 先由父类完成签名和过期时间等基础校验
        validated_token = super().get_validated_token(raw_token)

        try:
            redis_conn = get_redis_connection("default")
        except Exception as exc:
            logger.warning("JWT 认证：获取 Redis 连接失败，跳过 tokenVersion/黑名单校验: %s", exc)
            return validated_token

        try:
            # 1. 校验用户 Token 版本号（强制下线）
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

        except AuthenticationFailed:
            # 业务异常（token 版本过期 / 黑名单命中）—— 正常抛出
            raise
        except Exception as exc:
            # Redis 网络/超时等异常 —— 降级放行，不阻塞请求
            logger.warning("JWT 认证：Redis 查询异常，跳过 tokenVersion/黑名单校验: %s", exc)

        return validated_token
