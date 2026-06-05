"""系统管理-菜单模型。

"""

from django.db import models


class Menu(models.Model):
    """
    表名：sys_menu
    表说明：系统菜单表，用于记录前端菜单、路由及按钮权限等信息。
    """

    parent_id = models.BigIntegerField(verbose_name="父菜单ID", help_text="父菜单ID")
    tree_path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="父节点ID路径",
        help_text="父节点ID路径",
    )
    name = models.CharField(max_length=64, verbose_name="菜单名称", help_text="菜单名称")
    type = models.CharField(max_length=1, verbose_name="菜单类型", help_text="菜单类型（C-目录 M-菜单 B-按钮）")
    route_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="路由名称",
        help_text="路由名称（用于命名路由）",
    )
    route_path = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="路由路径",
        help_text="路由路径",
    )
    component = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="组件路径",
        help_text="组件路径（相对于前端视图路径）",
    )
    perm = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="权限标识",
        help_text="权限标识（按钮专用）",
    )
    always_show = models.SmallIntegerField(
        default=0,
        verbose_name="是否始终显示",
        help_text="【目录】仅一个子路由时是否始终显示（1-是, 0-否）",
    )
    keep_alive = models.SmallIntegerField(
        default=0,
        verbose_name="页面缓存",
        help_text="【菜单】是否开启页面缓存（1-是, 0-否）",
    )
    visible = models.SmallIntegerField(
        default=1,
        verbose_name="显示状态",
        help_text="显示状态（1-显示, 0-隐藏）",
    )
    sort = models.IntegerField(default=0, verbose_name="排序", help_text="排序")
    icon = models.CharField(max_length=64, blank=True, null=True, verbose_name="菜单图标", help_text="菜单图标")
    redirect = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name="跳转路径",
        help_text="跳转路径",
    )
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    params = models.JSONField(blank=True, null=True, verbose_name="路由参数", help_text="路由参数")

    class Meta:
        db_table = "sys_menu"
        verbose_name = "菜单表"
        verbose_name_plural = "菜单表"

    def __str__(self):
        return self.name
