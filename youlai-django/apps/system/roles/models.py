"""系统管理-角色模型。

"""

from django.db import models


class Role(models.Model):
    """
    表名：sys_role
    表说明：角色表，用于记录系统中各角色信息及其权限范围。
    """

    name = models.CharField(max_length=64, unique=True, verbose_name="角色名称", help_text="角色名称")
    code = models.CharField(max_length=32, unique=True, verbose_name="角色编码", help_text="角色编码")
    sort = models.IntegerField(blank=True, null=True, verbose_name="显示顺序", help_text="显示顺序")
    status = models.SmallIntegerField(default=1, verbose_name="状态", help_text="状态（1-正常, 0-停用）")
    data_scope = models.SmallIntegerField(
        blank=True,
        null=True,
        verbose_name="数据权限",
        help_text="数据权限（1-所有数据, 2-部门及子部门, 3-本部门, 4-本人, 5-自定义部门）",
    )
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="更新人ID", help_text="更新人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="逻辑删除", help_text="逻辑删除标识（0-未删除, 1-已删除）")

    class Meta:
        db_table = "sys_role"
        verbose_name = "角色表"
        verbose_name_plural = "角色表"

    def __str__(self):
        return self.name


class RoleMenu(models.Model):
    """
    表名：sys_role_menu
    表说明：记录角色与菜单之间的关联关系，定义每个角色可访问的菜单。
    """

    role = models.ForeignKey("Role", on_delete=models.CASCADE, verbose_name="角色ID", help_text="角色ID")
    menu = models.ForeignKey("Menu", on_delete=models.CASCADE, verbose_name="菜单ID", help_text="菜单ID")

    class Meta:
        db_table = "sys_role_menu"
        verbose_name = "角色菜单关联表"
        verbose_name_plural = "角色菜单关联表"
        unique_together = ("role", "menu")

    def __str__(self):
        return f"{self.role.name} - {self.menu.name}"


class RoleDept(models.Model):
    """
    表名：sys_role_dept
    表说明：记录角色与部门之间的关联关系，用于自定义数据权限。
    """

    role = models.ForeignKey("Role", on_delete=models.CASCADE, verbose_name="角色ID", help_text="角色ID")
    dept = models.ForeignKey("Department", on_delete=models.CASCADE, verbose_name="部门ID", help_text="部门ID")

    class Meta:
        db_table = "sys_role_dept"
        verbose_name = "角色部门关联表"
        verbose_name_plural = "角色部门关联表"
        unique_together = ("role", "dept")

    def __str__(self):
        return f"{self.role.name} - {self.dept.name}"
