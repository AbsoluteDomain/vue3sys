from django.db import models


class OperationLog(models.Model):
    """操作记录表"""
    
    OPERATION_TYPES = [
        ('create', '新增'),
        ('update', '修改'),
        ('delete', '删除'),
    ]
    
    user_id = models.BigIntegerField(verbose_name="操作用户ID")
    user_name = models.CharField(max_length=100, verbose_name="操作用户名")
    module = models.CharField(max_length=50, verbose_name="操作模块标识")
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name="操作类型")
    target_id = models.BigIntegerField(verbose_name="目标对象ID")
    target_name = models.CharField(max_length=255, verbose_name="目标对象名称")
    before_data = models.TextField(blank=True, null=True, verbose_name="修改前数据")
    after_data = models.TextField(blank=True, null=True, verbose_name="修改后数据")
    description = models.CharField(max_length=500, blank=True, verbose_name="操作描述")
    ip = models.CharField(max_length=45, blank=True, null=True, verbose_name="IP地址")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")

    class Meta:
        db_table = "sys_operation_log"
        verbose_name = "操作记录"
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.user_name} {self.get_operation_type_display()} {self.module}"
