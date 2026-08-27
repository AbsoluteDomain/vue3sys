"""平台-认证序列化器。

"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django_redis import get_redis_connection
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

import logging

logger = logging.getLogger(__name__)

User = get_user_model()


def _safe_redis_get(key, default=None):
    """安全地读 Redis：连不上或出错时降级返回 default，不让登录/刷新接口挂掉。"""
    try:
        return get_redis_connection("default").get(key)
    except Exception as e:
        logger.warning("Redis 不可用，降级放行（key=%s）: %s", key, e)
        return default


def _safe_redis_delete(key):
    """安全地删 Redis key：连不上时静默忽略。"""
    try:
        get_redis_connection("default").delete(key)
    except Exception as e:
        logger.warning("Redis 不可用，跳过 delete（key=%s）: %s", key, e)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        """在基础 JWT 上附加自定义声明"""
        token = super().get_token(user)

        version_key = f"auth:user:token_version:{user.id}"
        current_version = _safe_redis_get(version_key)
        token_version = int(current_version) if current_version is not None else 0

        token["tokenVersion"] = token_version

        return token

    def validate(self, attrs):
        # 判断是否启用验证码
        if getattr(settings, 'CAPTCHA_ENABLED', True):
            captcha_key = self.initial_data.get("captchaId")
            captcha_code = self.initial_data.get("captchaCode")
            if not captcha_key or not captcha_code:
                raise ValidationError({"code": "A0410", "msg": "缺少验证码信息（captchaId/captchaCode）"})

            stored_value = _safe_redis_get(captcha_key)
            if not stored_value:
                raise ValidationError({"code": "A0242", "msg": "用户验证码过期"})

            if captcha_code.lower() != stored_value.decode("utf-8").lower():
                raise ValidationError({"code": "A0240", "msg": "验证码错误"})

            _safe_redis_delete(captcha_key)
 
        # 检查用户状态
        username = attrs.get('username')
        try:
            user = User.objects.get(username=username)
            if user.status == 0:
                raise ValidationError({"code": "A0202", "msg": "用户账户被冻结"})
            if user.is_deleted == 1:
                raise ValidationError({"code": "A0201", "msg": "用户账户不存在"})
        except User.DoesNotExist:
            pass
 
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise ValidationError({"code": "A0210", "msg": "用户名或密码错误"})

        # 登录成功后，失效所有旧会话（同一账号只能在一个终端登录）
        from apps.auth.utils.session_utils import invalidate_user_sessions
        invalidate_user_sessions(self.user.id)

        # 用新的 tokenVersion 重新生成 token
        new_refresh = self.get_token(self.user)
        data["refresh"] = str(new_refresh)
        data["access"] = str(new_refresh.access_token)

        session_type = getattr(settings, 'SESSION_TYPE', 'jwt')
 
        # JWT 会话模式
        if session_type != 'redis-token':
            token_type = "Bearer"
            access_token = data.get("access")
            refresh_token = data.get("refresh")
            access_token_lifetime = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=5))
            expires_in = int(access_token_lifetime.total_seconds())
 
            return {
                "code": "00000",
                "data": {
                    "tokenType": token_type,
                    "accessToken": access_token,
                    "refreshToken": refresh_token,
                    "expiresIn": expires_in,
                },
                "msg": "成功"
            }
 
        # Redis 会话模式
        import uuid
        redis_conn = get_redis_connection("default")

        user = self.user
        user_id = user.id

        access_token = uuid.uuid4().hex
        refresh_token = uuid.uuid4().hex

        access_token_lifetime = settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME", timedelta(minutes=5))
        refresh_token_lifetime = settings.SIMPLE_JWT.get("REFRESH_TOKEN_LIFETIME", timedelta(days=30))
        access_expires_in = int(access_token_lifetime.total_seconds())
        refresh_expires_in = int(refresh_token_lifetime.total_seconds())

        # 获取多角色数据权限列表
        from core.permissions.data_scope import get_user_data_scopes
        data_scopes = get_user_data_scopes(user)
        roles = list(user.roles.values_list('code', flat=True))

        online_user = {
            "userId": user_id,
            "username": user.username,
            "deptId": getattr(user, "dept_id", None),
            "dataScopes": [
                {
                    "roleCode": ds.role_code,
                    "dataScope": ds.data_scope,
                    "customDeptIds": ds.custom_dept_ids
                }
                for ds in data_scopes
            ],
            "roles": roles,
        }

        try:
            redis_conn.setex(f"auth:token:access:{access_token}", access_expires_in, str(online_user))
            redis_conn.setex(f"auth:token:refresh:{refresh_token}", refresh_expires_in, str(online_user))
            redis_conn.setex(f"auth:user:access:{user_id}", access_expires_in, access_token)
            redis_conn.setex(f"auth:user:refresh:{user_id}", refresh_expires_in, refresh_token)
        except Exception as e:
            logger.warning("Redis 不可用，跳过会话写入（用户 %s）: %s", user_id, e)
 
        return {
            "code": "00000",
            "data": {
                "tokenType": "Bearer",
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expiresIn": access_expires_in,
            },
            "msg": "成功"
        }
 
 
class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        # 在调用父类 validate 之前保存原始的 refresh token 字符串
        raw_refresh_token = attrs.get("refresh")
        token_version = 0

        # 父类进行 refresh token 校验，生成新的 access token
        try:
            data = super().validate(attrs)
        except TokenError:
            raise ValidationError({"code": "A0231", "msg": "刷新令牌无效或已过期"})

        # 校验 refresh token 中的 tokenVersion 是否与 Redis 中一致
        # 防止用户修改密码后，旧的 refresh token 仍能刷新出新的 access token
        if raw_refresh_token:
            try:
                refresh = RefreshToken(raw_refresh_token)
                refresh_payload = refresh.payload
                user_id = refresh_payload.get("user_id")
                token_version = refresh_payload.get("tokenVersion", 0)

                if user_id is not None:
                    version_key = f"auth:user:token_version:{user_id}"
                    current_version = _safe_redis_get(version_key)
                    current_version_int = int(current_version) if current_version is not None else 0

                    if token_version < current_version_int:
                        raise ValidationError({"code": "A0231", "msg": "刷新令牌已失效，请重新登录"})
            except ValidationError:
                raise

        # 这里我们直接返回传入的 refresh token（不进行刷新令牌更新，如需要刷新刷新令牌，可开启 refresh token 轮换）
        refresh = RefreshToken(raw_refresh_token)
        data["refresh"] = str(refresh)

        # 更新新生成的 access token 中的 tokenVersion
        new_access_token = data.get("access")
        if new_access_token:
            import jwt
            jwt_secret = settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY)
            jwt_algorithm = settings.SIMPLE_JWT.get("ALGORITHM", "HS256")
            payload = jwt.decode(new_access_token, jwt_secret, algorithms=[jwt_algorithm])
            payload["tokenVersion"] = token_version
            new_access_token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
            data["access"] = new_access_token

        token_type = "Bearer"
        expires_in = int(settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME").total_seconds())

        return {
            "code": "00000",
            "data": {
                "tokenType": token_type,
                "accessToken": data.get("access"),
                "refreshToken": data.get("refresh"),
                "expiresIn": expires_in,
            },
            "msg": "成功"
        }
 
 
__all__ = [
    "CustomTokenObtainPairSerializer",
    "CustomTokenRefreshSerializer",
]
