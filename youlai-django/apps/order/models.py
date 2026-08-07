"""订单管理-模型定义。

对应数据库表 order_list，该表为外部系统同步数据，Django 不负责建表（managed=False）。
"""

from django.db import models


class OrderList(models.Model):
    """订单列表模型，对应数据库表 order_list。"""

    order_no = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="订单流水号",
        db_comment="订单流水号",
    )
    contract_no = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="合同编号",
        db_comment="合同编号",
    )
    customer_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="客户名称",
        db_comment="客户名称",
    )
    customer_no = models.IntegerField(
        blank=True, null=True, verbose_name="客户编号",
        db_comment="客户编号",
    )
    material_no = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="物料编号",
        db_comment="物料编号",
    )
    product_name = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="商品名称",
        db_comment="商品名称",
    )
    product_model = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="天链型号",
        db_comment="天链型号",
    )
    product_category = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="商品类别",
        db_comment="商品类别",
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name="订单数量", db_comment="订单数量",
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name="单价", db_comment="单价",
    )
    amount = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="金额",
        db_comment="金额",
    )
    tax_unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        verbose_name="含税单价", db_comment="含税单价",
    )
    tax_amount = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="含税金额",
        db_comment="含税金额",
    )
    order_date = models.DateTimeField(
        blank=True, null=True, verbose_name="订单日期",
        db_comment="订单日期",
    )
    delivery_date = models.DateTimeField(
        db_column="delivery date", blank=True, null=True,
        verbose_name="交付日期", db_comment="交付日期(需求货期)",
    )
    create_at = models.DateTimeField(
        blank=True, null=True, verbose_name="创建日期",
        db_comment="创建日期",
    )

    class Meta:
        managed = False
        db_table = "order_list"
        verbose_name = "订单"
        verbose_name_plural = "订单管理"

    def __str__(self):
        return self.order_no or f"Order-{self.id}"
