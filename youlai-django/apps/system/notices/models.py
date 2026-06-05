"""系统管理-通知公告模型。

"""

from django.db import models


class Notice(models.Model):
    """
    表名：sys_notice
    表说明：通知公告表，用于记录系统中发布的通知信息。
    """

    title = models.CharField(max_length=50, verbose_name="通知标题", help_text="通知标题")
    content = models.TextField(verbose_name="通知内容", help_text="通知内容")
    type = models.SmallIntegerField(verbose_name="通知类型", help_text="通知类型（关联字典编码：notice_type）")
    level = models.CharField(max_length=5, verbose_name="通知等级", help_text="通知等级（字典code：notice_level）")
    target_type = models.SmallIntegerField(verbose_name="目标类型", help_text="目标类型（1: 全体, 2: 指定）")
    target_user_ids = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="目标用户ID集合",
        help_text="目标用户ID集合（多个使用英文逗号分隔）",
    )
    publisher_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="发布人ID",
        help_text="发布人ID",
    )
    publish_status = models.SmallIntegerField(
        default=0,
        verbose_name="发布状态",
        help_text="发布状态（0: 未发布, 1: 已发布, -1: 已撤回）",
    )
    publish_time = models.DateTimeField(null=True, blank=True, verbose_name="发布时间", help_text="发布时间")
    revoke_time = models.DateTimeField(null=True, blank=True, verbose_name="撤回时间", help_text="撤回时间")
    create_by = models.BigIntegerField(verbose_name="创建人ID", help_text="创建人ID")
    create_time = models.DateTimeField(verbose_name="创建时间", help_text="创建时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="更新人ID", help_text="更新人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="是否删除", help_text="是否删除（0: 未删除, 1: 已删除）")

    class Meta:
        db_table = "sys_notice"
        verbose_name = "通知公告表"
        verbose_name_plural = "通知公告表"

    def __str__(self):
        return self.title


class UserNotice(models.Model):
    """
    表名：sys_user_notice
    表说明：用户通知公告表，用于记录用户对通知的接收与阅读状态。
    """

    notice = models.ForeignKey("Notice", on_delete=models.CASCADE, verbose_name="通知ID", help_text="通知ID")
    user = models.ForeignKey("User", on_delete=models.CASCADE, verbose_name="用户ID", help_text="用户ID")
    is_read = models.SmallIntegerField(default=0, verbose_name="读取状态", help_text="读取状态（0: 未读, 1: 已读）")
    read_time = models.DateTimeField(null=True, blank=True, verbose_name="阅读时间", help_text="阅读时间")
    create_time = models.DateTimeField(verbose_name="创建时间", help_text="创建时间")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="逻辑删除", help_text="逻辑删除（0: 未删除, 1: 已删除）")

    class Meta:
        db_table = "sys_user_notice"
        verbose_name = "用户通知公告表"
        verbose_name_plural = "用户通知公告表"

    def __str__(self):
        return f"Notice {self.notice.id} for User {self.user.username}"
