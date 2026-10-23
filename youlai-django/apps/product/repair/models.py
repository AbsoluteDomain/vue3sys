from django.db import models


class Repair(models.Model):
    STATUS_PENDING = 0
    STATUS_REPAIRED = 1
    STATUS_CHOICES = (
        (STATUS_PENDING, "待返修"),
        (STATUS_REPAIRED, "已返修"),
    )

    id = models.AutoField(primary_key=True, verbose_name="ID")
    product_id = models.IntegerField(verbose_name="成品ID")
    sn_code = models.CharField(max_length=100, verbose_name="成品SN码")
    product_model = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="产品型号",
        help_text="创建返修记录时从成品关联BOM同步",
    )
    repair_cnt = models.IntegerField(default=1, verbose_name="返修次数")
    repair_info = models.TextField(verbose_name="返修内容")
    repair_status = models.IntegerField(
        default=STATUS_PENDING,
        choices=STATUS_CHOICES,
        verbose_name="返修状态",
        help_text="0=待返修，1=已返修",
    )
    is_del = models.IntegerField(default=0, verbose_name="删除标记")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "repair"
        verbose_name = "返修记录"
        verbose_name_plural = "返修记录"