"""微信小程序认证序列化器。"""

from rest_framework import serializers


class WechatSilentLoginRequestSerializer(serializers.Serializer):
    """静默登录请求"""
    code = serializers.CharField(required=True, help_text="微信登录code")


class WechatPhoneLoginRequestSerializer(serializers.Serializer):
    """手机号快捷登录请求"""
    loginCode = serializers.CharField(required=True, help_text="微信登录code")
    phoneCode = serializers.CharField(required=True, help_text="微信手机号code")


class WechatBindMobileRequestSerializer(serializers.Serializer):
    """绑定手机号请求"""
    openId = serializers.CharField(required=True, help_text="微信openid")
    mobile = serializers.CharField(required=True, help_text="手机号")
    smsCode = serializers.CharField(required=True, help_text="短信验证码")


class WechatMiniappLoginResultSerializer(serializers.Serializer):
    """微信小程序登录结果"""
    needBindMobile = serializers.BooleanField(help_text="是否需要绑定手机号")
    accessToken = serializers.CharField(required=False, help_text="访问令牌")
    refreshToken = serializers.CharField(required=False, help_text="刷新令牌")
    expiresIn = serializers.IntegerField(required=False, help_text="令牌过期时间(秒)")
    tokenType = serializers.CharField(required=False, help_text="令牌类型")
    openId = serializers.CharField(required=False, help_text="微信openid（绑定手机号时使用）")
