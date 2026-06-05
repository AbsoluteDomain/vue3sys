"""系统管理-用户模型。

"""

from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    自定义用户模型，继承自 AbstractUser，增加了业务相关字段
    """

    nickname = models.CharField(max_length=64, blank=True, null=True, verbose_name="昵称", help_text="用户昵称")
    gender = models.SmallIntegerField(default=1, verbose_name="性别", help_text="性别（1-男, 2-女, 0-保密）")
    dept = models.ForeignKey(
        "Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="部门ID",
        help_text="部门ID",
    )
    avatar = models.CharField(max_length=255, blank=True, null=True, verbose_name="头像", help_text="用户头像")
    mobile = models.CharField(max_length=20, blank=True, null=True, verbose_name="联系方式", help_text="联系方式")
    status = models.SmallIntegerField(default=1, verbose_name="状态", help_text="状态（1-正常, 0-禁用）")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="更新人ID", help_text="更新人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="逻辑删除", help_text="逻辑删除标识（0-未删除, 1-已删除）")
    roles = models.ManyToManyField("Role", through="UserRole", verbose_name="角色", help_text="用户角色关联")

    # 设置 `related_name` 避免与默认 User 模型的 `groups` 和 `user_permissions` 字段产生冲突
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_user_groups",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_user_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    class Meta:
        db_table = "sys_user"
        verbose_name = "用户表"
        verbose_name_plural = "用户表"
        app_label = "system"

    def __str__(self):
        return self.username


class UserRole(models.Model):
    """
    表名：sys_user_role
    表说明：记录用户与角色之间的关联关系。
    """

    user = models.ForeignKey("User", on_delete=models.CASCADE, verbose_name="用户ID", help_text="用户ID")
    role = models.ForeignKey("Role", on_delete=models.CASCADE, verbose_name="角色ID", help_text="角色ID")

    class Meta:
        db_table = "sys_user_role"
        verbose_name = "用户角色关联表"
        verbose_name_plural = "用户角色关联表"
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"
