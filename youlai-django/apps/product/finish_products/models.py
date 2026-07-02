from django.db import models


class FinishProduct(models.Model):
    """成品表：BOM 组装成功后生成的成品记录"""

    STATUS_UNTESTED = 0
    STATUS_TESTING = 1
    STATUS_PASS = 2
    STATUS_FAIL = 3
    STATUS_CHOICES = (
        (STATUS_UNTESTED, "未测试"),
        (STATUS_TESTING, "测试中"),
        (STATUS_PASS, "测试合格"),
        (STATUS_FAIL, "测试不良"),
    )

    INVENTORY_NOT_IN = 0
    INVENTORY_IN = 1
    INVENTORY_OUT = 2
    INVENTORY_STOCK_CHOICES = (
        (INVENTORY_NOT_IN, "未入库"),
        (INVENTORY_IN, "入库"),
        (INVENTORY_OUT, "出库"),
    )

    REPAIR_NEW = 0
    REPAIR_REPAIRED = 1
    REPAIR_CHOICES = (
        (REPAIR_NEW, "新品"),
        (REPAIR_REPAIRED, "返修品"),
    )

    id = models.AutoField(primary_key=True, verbose_name="ID")
    sn_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="SN码",
        help_text="产品唯一标识",
    )
    bom_id = models.IntegerField(verbose_name="BOM ID")
    name = models.CharField(max_length=255, verbose_name="成品名称")
    status = models.IntegerField(
        default=STATUS_UNTESTED,
        choices=STATUS_CHOICES,
        verbose_name="测试状态",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="描述",
    )
    create_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="创建时间",
    )
    update_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="更新时间",
    )
    test_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="测试状态修改时间",
    )
    stock_in_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="入库时间",
    )
    stock_out_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="出库时间",
    )
    inventory_stock = models.IntegerField(
        default=INVENTORY_NOT_IN,
        choices=INVENTORY_STOCK_CHOICES,
        verbose_name="库存状态",
    )
    repair = models.IntegerField(
        default=REPAIR_NEW,
        choices=REPAIR_CHOICES,
        verbose_name="是否返修",
    )

    class Meta:
        db_table = "finish_product"
        verbose_name = "成品"
        verbose_name_plural = "成品"
        ordering = ["-create_time", "-id"]

    def __str__(self):
        return self.sn_code or f"{self.name}#{self.id}"
