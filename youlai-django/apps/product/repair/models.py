from django.db import models


class Repair(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    product_id = models.IntegerField(verbose_name="成品ID")
    sn_code = models.CharField(max_length=100, verbose_name="成品SN码")
    repair_cnt = models.IntegerField(default=1, verbose_name="返修次数")
    repair_info = models.TextField(verbose_name="返修内容")
    is_del = models.IntegerField(default=0, verbose_name="删除标记")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "repair"
        verbose_name = "返修记录"
        verbose_name_plural = "返修记录"