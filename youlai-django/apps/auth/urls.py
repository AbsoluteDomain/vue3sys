"""平台-认证路由。

"""

from django.urls import path

from .views import AuthViewSet
from .views_wechat import WechatMiniappAuthViewSet

urlpatterns = [
    path("login", AuthViewSet.as_view({"post": "login"}), name="token_obtain_pair"),
    path("login/sms", AuthViewSet.as_view({"post": "login_by_sms"}), name="login_by_sms"),
    path("sms/code", AuthViewSet.as_view({"post": "send_sms_login_code"}), name="send_sms_login_code"),
    path("captcha", AuthViewSet.as_view({"get": "captcha"}), name="captcha"),
    path("refresh-token", AuthViewSet.as_view({"post": "refresh_token"}), name="token_refresh"),
    path("logout", AuthViewSet.as_view({"delete": "logout"}), name="logout"),
    # 微信小程序认证
    path("wechat/miniapp/auth/silent-login", WechatMiniappAuthViewSet.as_view({"post": "silent_login"}), name="wechat_silent_login"),
    path("wechat/miniapp/auth/phone-login", WechatMiniappAuthViewSet.as_view({"post": "phone_login"}), name="wechat_phone_login"),
    path("wechat/miniapp/auth/bind-mobile", WechatMiniappAuthViewSet.as_view({"post": "bind_mobile"}), name="wechat_bind_mobile"),
]
