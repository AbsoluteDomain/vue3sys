"""用户第三方账号绑定模型。"""

from django.db import models


class SocialPlatform(models.TextChoices):
    """社交平台枚举"""
    WECHAT_MINI = "WECHAT_MINI", "微信小程序"
    WECHAT_MP = "WECHAT_MP", "微信公众号"
    ALIPAY = "ALIPAY", "支付宝"
    QQ = "QQ", "QQ"
    APPLE = "APPLE", "Apple"


class UserSocial(models.Model):
    """用户第三方账号绑定表"""

    id = models.BigAutoField(primary_key=True)
    user_id = models.BigIntegerField(verbose_name="用户ID")
    platform = models.CharField(
        max_length=20,
        choices=SocialPlatform.choices,
        verbose_name="平台类型"
    )
    openid = models.CharField(max_length=64, verbose_name="平台openid")
    unionid = models.CharField(max_length=64, null=True, blank=True, verbose_name="微信unionid")
    nickname = models.CharField(max_length=64, null=True, blank=True, verbose_name="第三方昵称")
    avatar = models.CharField(max_length=255, null=True, blank=True, verbose_name="第三方头像URL")
    session_key = models.CharField(max_length=128, null=True, blank=True, verbose_name="微信session_key")
    verified = models.SmallIntegerField(default=1, verbose_name="是否已验证(1-已验证 0-未验证)")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="绑定时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "sys_user_social"
        verbose_name = "用户第三方账号绑定"
        unique_together = [("platform", "openid")]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["unionid"]),
        ]

    def __str__(self):
        return f"{self.platform}:{self.openid}"
