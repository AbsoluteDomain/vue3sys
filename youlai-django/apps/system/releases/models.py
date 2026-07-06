"""系统版本更新公告模型。"""

from django.db import models


class Release(models.Model):
    """表名：sys_release"""

    RELEASE_TYPE_NORMAL = 1
    RELEASE_TYPE_IMPORTANT = 2
    RELEASE_TYPE_URGENT = 3

    PUBLISH_DRAFT = 0
    PUBLISH_PUBLISHED = 1
    PUBLISH_REVOKED = -1

    version = models.CharField(max_length=32, verbose_name="版本号")
    title = models.CharField(max_length=100, verbose_name="公告标题")
    summary = models.CharField(max_length=500, blank=True, null=True, verbose_name="摘要")
    release_type = models.SmallIntegerField(default=RELEASE_TYPE_NORMAL, verbose_name="发布类型")
    publish_status = models.SmallIntegerField(default=PUBLISH_DRAFT, verbose_name="发布状态")
    publish_time = models.DateTimeField(null=True, blank=True, verbose_name="发布时间")
    revoke_time = models.DateTimeField(null=True, blank=True, verbose_name="撤回时间")
    force_notify = models.SmallIntegerField(default=1, verbose_name="登录弹窗提醒")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID")
    create_time = models.DateTimeField(verbose_name="创建时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="更新人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="是否删除")

    class Meta:
        db_table = "sys_release"
        verbose_name = "版本更新公告"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.version} - {self.title}"


class ReleaseItem(models.Model):
    """表名：sys_release_item"""

    ITEM_TYPE_FEATURE = 1
    ITEM_TYPE_OPTIMIZE = 2
    ITEM_TYPE_FIX = 3
    ITEM_TYPE_OTHER = 4

    ITEM_TYPE_LABELS = {
        ITEM_TYPE_FEATURE: "新功能",
        ITEM_TYPE_OPTIMIZE: "优化",
        ITEM_TYPE_FIX: "修复",
        ITEM_TYPE_OTHER: "其他",
    }

    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        db_column="release_id",
        related_name="items",
        verbose_name="公告ID",
    )
    item_type = models.SmallIntegerField(default=ITEM_TYPE_FEATURE, verbose_name="条目类型")
    content = models.CharField(max_length=500, verbose_name="条目内容")
    sort = models.IntegerField(default=0, verbose_name="排序")
    create_time = models.DateTimeField(verbose_name="创建时间")

    class Meta:
        db_table = "sys_release_item"
        verbose_name = "版本更新公告明细"
        verbose_name_plural = verbose_name
        ordering = ["sort", "id"]

    def __str__(self):
        return self.content[:50]


class UserReleaseRead(models.Model):
    """表名：sys_user_release_read"""

    user_id = models.BigIntegerField(verbose_name="用户ID")
    release = models.ForeignKey(
        Release,
        on_delete=models.CASCADE,
        db_column="release_id",
        related_name="user_reads",
        verbose_name="公告ID",
    )
    is_read = models.SmallIntegerField(default=0, verbose_name="是否已读")
    read_time = models.DateTimeField(null=True, blank=True, verbose_name="阅读时间")
    create_time = models.DateTimeField(verbose_name="创建时间")

    class Meta:
        db_table = "sys_user_release_read"
        verbose_name = "用户版本公告阅读记录"
        verbose_name_plural = verbose_name
        unique_together = [("user_id", "release")]

    def __str__(self):
        return f"user={self.user_id} release={self.release_id}"
