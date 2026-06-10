"""认证相关的视图函数。"""

import time
import jwt
from django.conf import settings
from django_redis import get_redis_connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.tokens import RefreshToken

from core.openapi import resp
from rest_framework.response import Response
from core.response import error, success
from apps.system.utils.mobile_utils import send_mobile_code, verify_mobile_code

from django.contrib.auth import get_user_model

from .serializers import CustomTokenObtainPairSerializer, CustomTokenRefreshSerializer
from .utils.auth_utils import generate_captcha

User = get_user_model()

@extend_schema(tags=["01.认证接口"])
class AuthViewSet(ViewSet):
    """平台-认证视图。"""
    permission_classes = [AllowAny]
    # 认证接口不应强制校验 JWT，否则 token 失效时无法调用 logout 完成黑名单清理
    authentication_classes = []

    @extend_schema(summary="登录")
    def login(self, request, *args, **kwargs):
        serializer = CustomTokenObtainPairSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @extend_schema(summary="发送登录短信验证码")
    def send_sms_login_code(self, request, *args, **kwargs):
        mobile = (request.query_params.get("mobile") or "").strip()
        if not mobile:
            return error("缺少 mobile 参数", code="A0410", status=400)

        result = send_mobile_code(mobile)
        if not result.get("success"):
            return error(result.get("message") or "短信发送失败", code="A0500", status=500)

        return success(None)

    @extend_schema(summary="短信验证码登录")
    def login_by_sms(self, request, *args, **kwargs):
        mobile = (request.query_params.get("mobile") or "").strip()
        code = (request.query_params.get("code") or "").strip()

        if not mobile or not code:
            return error("缺少 mobile/code 参数", code="A0410", status=400)

        ok = verify_mobile_code(mobile, code)
        if not ok:
            return error("验证码错误或已过期", code="A0240", status=400)

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            return error("用户账户不存在", code="A0201", status=400)

        if getattr(user, "is_deleted", 0) == 1:
            return error("用户账户不存在", code="A0201", status=400)

        if getattr(user, "status", 1) == 0:
            return error("用户账户被冻结", code="A0202", status=400)

        session_type = getattr(settings, 'SESSION_TYPE', 'jwt')
        if session_type == 'redis-token':
            # 当前工程 redis-token 模式的 token 生成逻辑仅在账号密码登录序列化器中实现。
            return error("当前会话模式不支持短信验证码登录", code="A0500", status=500)

        refresh = RefreshToken.for_user(user)

        redis_conn = get_redis_connection("default")
        version_key = f"auth:user:security_version:{user.id}"
        current_version = redis_conn.get(version_key)
        security_version = int(current_version) if current_version is not None else 0
        refresh["securityVersion"] = security_version

        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        token_type = "Bearer"
        expires_in = int(settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME").total_seconds())

        return Response(
            {
                "code": "00000",
                "data": {
                    "tokenType": token_type,
                    "accessToken": access_token,
                    "refreshToken": refresh_token,
                    "expiresIn": expires_in,
                },
                "msg": "成功",
            }
        )

    @extend_schema(summary="令牌刷新")
    def refresh_token(self, request, *args, **kwargs):
        refresh_token = request.query_params.get("refreshToken")
        if not refresh_token:
            return error("缺少 refreshToken 参数", code="A0410", status=400)
        # 刷新令牌
        serializer = CustomTokenRefreshSerializer(data={"refresh": refresh_token}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @extend_schema(
        summary="获取验证码",
        responses=resp(
            "CaptchaResult",
            inline_serializer(
                name="CaptchaData",
                fields={
                    "captchaId": serializers.CharField(),
                    "captchaBase64": serializers.CharField(),
                },
            ),
        ),
    )
    def captcha(self, request, *args, **kwargs):
        captcha_data = generate_captcha()
        return success(captcha_data)

    @extend_schema(
        summary="退出登录",
        responses=resp("LogoutResult", serializers.JSONField(required=False, allow_null=True)),
    )
    def logout(self, request, *args, **kwargs):
        # 获取请求头中的 Authorization 信息
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return success(None)

        # 提取 token 字符串
        token = auth_header.split()[1]

        # 解码 token 获取过期时间
        token_backend = TokenBackend(algorithm="HS256")
        try:
            # 忽略过期时间的验证
            token_data = token_backend.decode(token, verify=False)
        except jwt.DecodeError:
            return success(None)

        now = int(time.time())
        exp = token_data.get("exp", now)
        remaining_seconds = exp - now
        if remaining_seconds <= 0:
            remaining_seconds = 0

        # 将 token 存入黑名单
        redis_conn = get_redis_connection("default")
        jti = token_data.get("jti")
        if remaining_seconds and jti:
            redis_conn.setex(f"auth:token:blacklist:{jti}", remaining_seconds, "1")

        return success(None)

__all__ = [
    "AuthViewSet",
]
