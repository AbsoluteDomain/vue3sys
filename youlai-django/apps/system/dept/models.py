"""系统管理-部门模型。

"""

from django.db import models


class Department(models.Model):
    """
    表名：sys_dept
    表说明：部门表，用于记录公司或组织的部门信息。
    """

    name = models.CharField(max_length=100, verbose_name="部门名称", help_text="部门名称")
    code = models.CharField(max_length=100, unique=True, verbose_name="部门编号", help_text="部门编号")
    parent_id = models.BigIntegerField(default=0, verbose_name="父节点ID", help_text="父节点ID")
    tree_path = models.CharField(max_length=255, verbose_name="父节点ID路径", help_text="父节点ID路径")
    sort = models.SmallIntegerField(default=0, verbose_name="显示顺序", help_text="显示顺序")
    status = models.SmallIntegerField(default=1, verbose_name="状态", help_text="状态（1-正常 0-禁用）")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="修改人ID", help_text="修改人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="逻辑删除标识", help_text="逻辑删除标识（1-已删除 0-未删除）")

    class Meta:
        db_table = "sys_dept"
        verbose_name = "部门表"
        verbose_name_plural = "部门表"

    def __str__(self):
        return self.name
