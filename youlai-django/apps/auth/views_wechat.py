"""微信小程序认证视图。"""

import logging
import uuid
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django_redis import get_redis_connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from core.response import error, success
from .models import UserSocial, SocialPlatform
from .serializers_wechat import (
    WechatSilentLoginRequestSerializer,
    WechatPhoneLoginRequestSerializer,
    WechatBindMobileRequestSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(tags=["13.微信小程序认证"])
class WechatMiniappAuthViewSet(ViewSet):
    """微信小程序认证视图"""
    permission_classes = [AllowAny]

    @extend_schema(summary="静默登录", request=WechatSilentLoginRequestSerializer)
    def silent_login(self, request):
        """静默登录"""
        serializer = WechatSilentLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        # 获取微信会话信息
        session = self._get_jscode_session(code)
        open_id = session.get("openid")

        if not open_id:
            return error("微信登录失败：无法获取用户标识", code="A0200", status=400)

        # 查找是否已绑定用户
        try:
            social = UserSocial.objects.get(platform=SocialPlatform.WECHAT_MINI, openid=open_id)
            # 已绑定用户，直接登录
            token = self._generate_token_by_user_id(social.user_id)
            return success({
                "needBindMobile": False,
                **token
            })
        except UserSocial.DoesNotExist:
            # 未绑定用户，返回需要绑定手机号
            logger.info(f"微信小程序静默登录：用户未绑定手机号，openId={open_id}")
            return success({
                "needBindMobile": True,
                "openId": open_id
            })

    @extend_schema(summary="手机号快捷登录", request=WechatPhoneLoginRequestSerializer)
    def phone_login(self, request):
        """手机号快捷登录"""
        serializer = WechatPhoneLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        login_code = serializer.validated_data["loginCode"]
        phone_code = serializer.validated_data["phoneCode"]

        # 获取微信会话信息
        session = self._get_jscode_session(login_code)
        open_id = session["openid"]

        # 获取手机号
        mobile = self._get_phone_number(phone_code)

        logger.info(f"微信小程序手机号快捷登录：openId={open_id}, mobile={mobile}")

        # 查询或创建用户
        user = self._find_or_create_user(mobile)

        # 绑定微信 openid
        self._bind_wechat_openid(user.id, open_id, session.get("unionid"), session.get("session_key"))

        # 生成认证令牌
        token = self._generate_token_by_user(user)
        return success(token, msg="登录成功")

    @extend_schema(summary="绑定手机号", request=WechatBindMobileRequestSerializer)
    def bind_mobile(self, request):
        """绑定手机号"""
        serializer = WechatBindMobileRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        open_id = serializer.validated_data["openId"]
        mobile = serializer.validated_data["mobile"]
        sms_code = serializer.validated_data["smsCode"]

        # 验证短信验证码
        redis_conn = get_redis_connection("default")
        cache_key = f"sms:login:{mobile}"
        cached = redis_conn.get(cache_key)

        if not cached:
            return error("验证码已过期", code="A0242", status=400)

        if cached.decode() != sms_code:
            return error("验证码错误", code="A0240", status=400)

        # 删除验证码
        redis_conn.delete(cache_key)

        # 查询或创建用户
        user = self._find_or_create_user(mobile)

        # 绑定微信 openid
        self._bind_wechat_openid(user.id, open_id, None, None)

        logger.info(f"微信小程序绑定手机号成功：mobile={mobile}, openId={open_id}")

        # 生成认证令牌
        token = self._generate_token_by_user(user)
        return success(token, msg="绑定成功")

    # ==================== 私有方法 ====================

    def _get_jscode_session(self, code: str) -> dict:
        """获取微信会话信息"""
        app_id = getattr(settings, "WX_MINIAPP_APP_ID", "")
        app_secret = getattr(settings, "WX_MINIAPP_APP_SECRET", "")

        url = f"https://api.weixin.qq.com/sns/jscode2session?appid={app_id}&secret={app_secret}&js_code={code}&grant_type=authorization_code"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get("errcode", 0) != 0:
                logger.error(f"获取微信会话信息失败：code={code}, errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
                raise Exception(data.get("errmsg", "Unknown error"))

            return data
        except Exception as e:
            logger.error(f"获取微信会话信息失败：code={code}, error={str(e)}")
            raise Exception(f"微信登录失败：{str(e)}")

    def _get_phone_number(self, phone_code: str) -> str:
        """获取微信手机号"""
        access_token = self._get_access_token()

        url = f"https://api.weixin.qq.com/wxa/business/getuserphonenumber?access_token={access_token}&code={phone_code}"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get("errcode", 0) != 0:
                logger.error(f"获取微信手机号失败：phoneCode={phone_code}, errcode={data.get('errcode')}, errmsg={data.get('errmsg')}")
                raise Exception(data.get("errmsg", "Unknown error"))

            return data.get("phone_info", {}).get("phoneNumber", "")
        except Exception as e:
            logger.error(f"获取微信手机号失败：phoneCode={phone_code}, error={str(e)}")
            raise Exception(f"获取手机号失败：{str(e)}")

    def _get_access_token(self) -> str:
        """获取微信 AccessToken"""
        app_id = getattr(settings, "WX_MINIAPP_APP_ID", "")
        app_secret = getattr(settings, "WX_MINIAPP_APP_SECRET", "")

        redis_conn = get_redis_connection("default")
        cache_key = f"wechat:access_token:{app_id}"

        # 先从缓存获取
        cached = redis_conn.get(cache_key)
        if cached:
            return cached.decode()

        # 请求新 token
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={app_id}&secret={app_secret}"

        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("errcode", 0) != 0:
            raise Exception(f"获取微信AccessToken失败：{data.get('errmsg')}")

        # 缓存 token（提前5分钟过期）
        expires_in = max((data.get("expires_in", 7200) - 300), 60)
        redis_conn.setex(cache_key, expires_in, data["access_token"])

        return data["access_token"]

    def _find_or_create_user(self, mobile: str):
        """查询或创建用户"""
        try:
            return User.objects.get(mobile=mobile, is_deleted=0)
        except User.DoesNotExist:
            pass

        # 创建新用户
        with transaction.atomic():
            user = User.objects.create(
                username=f"wx_{uuid.uuid4().hex[:8]}",
                nickname="微信用户",
                mobile=mobile,
                status=1,
                is_deleted=0,
            )

            # 分配 GUEST 角色（角色ID=3）
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                    [user.id, 3]
                )

            logger.info(f"微信小程序登录：创建新用户，mobile={mobile}, userId={user.id}")
            return user

    def _bind_wechat_openid(self, user_id: int, open_id: str, unionid: str = None, session_key: str = None):
        """绑定微信 openid"""
        try:
            social, created = UserSocial.objects.get_or_create(
                platform=SocialPlatform.WECHAT_MINI,
                openid=open_id,
                defaults={
                    "user_id": user_id,
                    "unionid": unionid,
                    "session_key": session_key,
                    "verified": 1,
                }
            )

            if not created:
                social.user_id = user_id
                social.unionid = unionid
                social.session_key = session_key
                social.save()
        except Exception as e:
            # 绑定失败不影响登录
            logger.warning(f"绑定微信 openid 失败：userId={user_id}, openId={open_id}, error={str(e)}")

    def _generate_token_by_user_id(self, user_id: int) -> dict:
        """根据用户ID生成Token"""
        try:
            user = User.objects.get(id=user_id, is_deleted=0)
        except User.DoesNotExist:
            raise Exception("用户不存在")

        return self._generate_token_by_user(user)

    def _generate_token_by_user(self, user) -> dict:
        """根据用户生成Token"""
        refresh = RefreshToken.for_user(user)

        return {
            "accessToken": str(refresh.access_token),
            "refreshToken": str(refresh),
            "expiresIn": getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME", 7200).total_seconds() if hasattr(getattr(settings, "SIMPLE_JWT", {}).get("ACCESS_TOKEN_LIFETIME", 7200), "total_seconds") else 7200,
            "tokenType": "Bearer",
        }
