"""平台-认证模块 - Redis Token 认证。

基于 Redis 的访问令牌认证实现，支持：
- Access Token + Refresh Token 双令牌机制
- 单设备/多设备登录控制
- 用户级会话失效
- 在线用户管理
"""

from __future__ import annotations

import json
import time
from typing import Optional, Tuple, Any

import uuid
from django_redis import get_redis_connection
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model

from apps.auth.models import UserSession

User = get_user_model()

# Redis Key 常量
class RedisKeys:
    # 访问令牌 -> 用户会话信息
    ACCESS_TOKEN_USER = "auth:token:access:{}"
    # 刷新令牌 -> 用户会话信息
    REFRESH_TOKEN_USER = "auth:token:refresh:{}"
    # 用户ID -> 访问令牌
    USER_ACCESS_TOKEN = "auth:user:access:{}"
    # 用户ID -> 刷新令牌
    USER_REFRESH_TOKEN = "auth:user:refresh:{}"
    # 已撤销 Token 的 JTI
    BLACKLIST_TOKEN = "auth:token:blacklist:{}"
    # 用户 Token 生效起点（tokenValidAfter）
    USER_TOKEN_VALID_AFTER = "auth:user:token_valid_after:{}"


# tokenValidAfter 默认过期时间（7天），避免Redis内存泄漏
TOKEN_VALID_AFTER_TTL_SECONDS = 7 * 24 * 60 * 60


class RedisTokenManager:
    """Redis Token 管理器。
    
    实现基于Redis的有状态认证，支持：
    - Access Token + Refresh Token 双令牌机制
    - 单设备/多设备登录控制
    - 用户级会话失效
    - 在线用户管理
    """

    def __init__(self, redis_conn=None):
        self._redis = redis_conn or get_redis_connection("default")

    def generate_token(self, user_session: UserSession, access_ttl: int = 3600, refresh_ttl: int = 604800) -> dict:
        """生成 Token。
        
        Args:
            user_session: 用户会话信息
            access_ttl: 访问令牌有效期（秒）
            refresh_ttl: 刷新令牌有效期（秒）
            
        Returns:
            包含 accessToken, refreshToken, expiresIn 的字典
        """
        access_token = uuid.uuid4().hex
        refresh_token = uuid.uuid4().hex

        # 存储访问令牌 -> 用户会话信息
        access_key = RedisKeys.ACCESS_TOKEN_USER.format(access_token)
        self._redis.setex(
            access_key,
            access_ttl,
            json.dumps(user_session.to_dict())
        )

        # 存储刷新令牌 -> 用户会话信息
        refresh_key = RedisKeys.REFRESH_TOKEN_USER.format(refresh_token)
        self._redis.setex(
            refresh_key,
            refresh_ttl,
            json.dumps(user_session.to_dict())
        )

        # 存储用户ID -> 刷新令牌
        user_refresh_key = RedisKeys.USER_REFRESH_TOKEN.format(user_session.user_id)
        self._redis.setex(user_refresh_key, refresh_ttl, refresh_token)

        return {
            'accessToken': access_token,
            'refreshToken': refresh_token,
            'expiresIn': access_ttl
        }

    def parse_token(self, token: str) -> Optional[UserSession]:
        """解析 Token 获取用户会话信息。
        
        Args:
            token: 访问令牌
            
        Returns:
            用户会话信息，无效时返回 None
        """
        key = RedisKeys.ACCESS_TOKEN_USER.format(token)
        raw = self._redis.get(key)
        if not raw:
            return None

        try:
            data = json.loads(raw)
            return UserSession.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def validate_token(self, token: str) -> bool:
        """校验 Token 是否有效。
        
        Args:
            token: 访问令牌
            
        Returns:
            是否有效
        """
        key = RedisKeys.ACCESS_TOKEN_USER.format(token)
        return self._redis.exists(key)

    def invalidate_token(self, token: str) -> None:
        """使访问令牌失效。
        
        Args:
            token: 访问令牌
        """
        key = RedisKeys.ACCESS_TOKEN_USER.format(token)
        raw = self._redis.get(key)
        if raw:
            try:
                data = json.loads(raw)
                user_id = data.get('user_id')
                if user_id:
                    self.invalidate_user_sessions(user_id)
            except json.JSONDecodeError:
                pass
        self._redis.delete(key)

    def invalidate_user_sessions(self, user_id: int) -> None:
        """使指定用户的所有会话失效。
        
        适用场景：用户修改密码、管理员强制下线、账号封禁等。
        
        Args:
            user_id: 用户ID
        """
        # 1. 删除访问令牌相关
        user_access_key = RedisKeys.USER_ACCESS_TOKEN.format(user_id)
        access_token = self._redis.get(user_access_key)
        if access_token:
            access_key = RedisKeys.ACCESS_TOKEN_USER.format(access_token.decode())
            self._redis.delete(access_key)
        self._redis.delete(user_access_key)

        # 2. 删除刷新令牌相关
        user_refresh_key = RedisKeys.USER_REFRESH_TOKEN.format(user_id)
        refresh_token = self._redis.get(user_refresh_key)
        if refresh_token:
            refresh_key = RedisKeys.REFRESH_TOKEN_USER.format(refresh_token.decode())
            self._redis.delete(refresh_key)
        self._redis.delete(user_refresh_key)

    def set_token_valid_after(self, user_id: int) -> None:
        """设置用户 Token 生效时间点。
        
        用于JWT模式下的会话失效控制，设置TTL防止Redis内存泄漏。
        
        Args:
            user_id: 用户ID
        """
        key = RedisKeys.USER_TOKEN_VALID_AFTER.format(user_id)
        self._redis.setex(key, TOKEN_VALID_AFTER_TTL_SECONDS, int(time.time()))

    def get_token_valid_after(self, user_id: int) -> Optional[int]:
        """获取用户 Token 生效时间点。
        
        Args:
            user_id: 用户ID
            
        Returns:
            生效时间戳，不存在返回 None
        """
        key = RedisKeys.USER_TOKEN_VALID_AFTER.format(user_id)
        value = self._redis.get(key)
        return int(value) if value else None


class RedisTokenAuthentication(BaseAuthentication):
    """基于 Redis 的访问令牌认证。

    - 从 Authorization: Bearer <accessToken> 中获取访问令牌
    - 通过 Redis 映射 auth:token:access:{accessToken} -> UserSession
    - 未命中或已过期视为未认证
    """

    def __init__(self):
        self._token_manager = RedisTokenManager()

    def authenticate(self, request) -> Optional[Tuple[Any, None]]:
        """认证请求。
        
        Args:
            request: HTTP请求对象
            
        Returns:
            (user, auth) 元组，认证失败返回 None 或抛出异常
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        access_token = auth_header.split()[1]
        
        user_session = self._token_manager.parse_token(access_token)
        if not user_session:
            raise AuthenticationFailed("无效或过期的访问令牌", code="token_invalid")

        # 构造一个简单的用户对象用于请求上下文
        request.user_session = user_session
        
        # 返回 (user, auth)，这里 user 可以是 None，因为我们通过 request.user_session 存储
        return (None, None)
