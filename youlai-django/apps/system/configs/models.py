"""系统管理-配置模型。

"""

from django.db import models


class SysConfig(models.Model):
    """
    表名：sys_config
    表说明：系统配置表，用于存储系统运行时的各项配置参数。
    """

    config_name = models.CharField(max_length=50, verbose_name="配置名称", help_text="配置名称")
    config_key = models.CharField(max_length=50, verbose_name="配置Key", help_text="配置Key")
    config_value = models.CharField(max_length=100, verbose_name="配置值", help_text="配置值")
    remark = models.CharField(max_length=255, blank=True, null=True, verbose_name="备注", help_text="备注")
    create_time = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    create_by = models.BigIntegerField(null=True, blank=True, verbose_name="创建人ID", help_text="创建人ID")
    update_time = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")
    update_by = models.BigIntegerField(null=True, blank=True, verbose_name="更新人ID", help_text="更新人ID")
    is_deleted = models.SmallIntegerField(default=0, verbose_name="逻辑删除", help_text="逻辑删除标识（0-未删除, 1-已删除）")

    class Meta:
        db_table = "sys_config"
        verbose_name = "系统配置表"
        verbose_name_plural = "系统配置表"

    def __str__(self):
        return self.config_name
