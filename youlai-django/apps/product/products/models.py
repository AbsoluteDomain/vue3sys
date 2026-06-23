from django.db import models

from .constants import PRODUCT_TYPE_CHOICES, PRODUCT_TYPE_SELF_MADE


class Product(models.Model):
    """
    产品表 (对应数据库表: products)
    """
    # 1. id: int, 主键, 非空
    # Django 默认会自动创建一个名为 id 的 AutoField 作为主键，
    # 所以这里可以省略，或者显式写出来。
    id = models.AutoField(primary_key=True, verbose_name="ID")

    # 2. name: varchar(255), 非空
    name = models.CharField(max_length=255, null=False, verbose_name="产品名称")

    # 3. type: int, 0=自制 1=外协 2=外购
    type = models.IntegerField(
        choices=PRODUCT_TYPE_CHOICES,
        default=PRODUCT_TYPE_SELF_MADE,
        verbose_name="产品类型",
    )

    draw_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="图号",
    )
    material_code = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="物料编码",
    )

    # 4. quantity: int, 允许空
    # 注意：数据库中允许空，Django中对应 null=True。
    # 如果要在表单中也允许为空，通常加上 blank=True。
    quantity = models.IntegerField(null=True, blank=True, verbose_name="数量")

    # 5. unit: varchar(255), 允许空
    unit = models.CharField(max_length=255, null=True, blank=True, verbose_name="单位")

    # 6. location: varchar(255), 允许空
    location = models.CharField(max_length=255, null=True, blank=True, verbose_name="位置")

    # 7. description: varchar(255), 允许空
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name="描述")

    # 8. updated_at: datetime, 允许空
    # auto_now=True 会在每次保存时自动更新为当前时间
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")

    # 9. alert_quantity: int, 允许空
    alert_quantity = models.IntegerField(null=True, blank=True, verbose_name="预警数量")

    # 10. is_del: 逻辑删除标记，0=正常，1=已删除
    is_del = models.IntegerField(default=0, verbose_name="删除标记")

    class Meta:
        # 关键点：指定数据库中的表名
        # 根据你的截图，表名似乎是 'products'
        db_table = 'products'
        verbose_name = "产品"
        verbose_name_plural = "产品管理"

    def __str__(self):
        # 定义打印对象时显示的字符，这里显示产品名
        return self.name