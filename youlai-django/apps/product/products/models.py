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

    # 10. procurement_cycle: decimal, 采购周期（天）
    procurement_cycle = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0, verbose_name="采购周期(天)")

    # 11. is_del: 逻辑删除标记，0=正常，1=已删除
    is_del = models.IntegerField(default=0, verbose_name="删除标记")

    class Meta:
        # 关键点：指定数据库中的表名
        # 根据你的截图，表名似乎是 'products'
        db_table = 'products'
        app_label = 'products'
        verbose_name = "产品"
        verbose_name_plural = "产品管理"

    def __str__(self):
        # 定义打印对象时显示的字符，这里显示产品名
        return self.name


class WarehouseLog(models.Model):
    """
    库存操作日志表 (对应数据库表: warehouse_log)
    
    记录所有库存相关的操作，包括：
    - 出入库操作
    - 绑定/解除绑定关节到机械臂
    - 成品回退
    - 其他影响库存的操作
    
    设计原则：
    - 1次操作即使造成多条数据库修改，也只生成1条记录
    - 日志中记录对数据的所有操作详情
    - 尽量记录操作来源模块，便于溯源
    """
    STORAGE_IN = 1       # 入库
    STORAGE_OUT_SALE = 2  # 出库(外销)
    STORAGE_OUT_RANDD = 3  # 出库(研发)
    BIND = 4              # 绑定（关节绑定到机械臂）
    UNBIND = 5            # 解除绑定
    ROLLBACK = 6          # 成品回退
    MANUAL_ADJUST = 7     # 手动调整
    STORAGE_OUT_EXCHANGE = 8  # 出库(换货)
    STORAGE_OUT_SCRAP = 9     # 出库(报废)
    
    STORAGE_CHOICES = (
        (STORAGE_IN, '入库'),
        (STORAGE_OUT_SALE, '出库(外销)'),
        (STORAGE_OUT_RANDD, '出库(研发)'),
        (BIND, '绑定关节'),
        (UNBIND, '解除绑定关节'),
        (ROLLBACK, '成品回退'),
        (MANUAL_ADJUST, '手动调整'),
        (STORAGE_OUT_EXCHANGE, '出库(换货)'),
        (STORAGE_OUT_SCRAP, '出库(报废)'),
    )
    
    # 操作来源模块
    MODULE_FINISH_PRODUCT = 'finish_product'  # 成品管理
    MODULE_INVENTORY = 'inventory'            # 库存管理
    MODULE_REPAIR = 'repair'                  # 返修管理
    MODULE_ASSEMBLE = 'assemble'              # 组装产品
    MODULE_MANUAL = 'manual'                  # 手动操作
    
    MODULE_CHOICES = (
        (MODULE_FINISH_PRODUCT, '成品管理'),
        (MODULE_INVENTORY, '库存管理'),
        (MODULE_REPAIR, '返修管理'),
        (MODULE_ASSEMBLE, '组装产品'),
        (MODULE_MANUAL, '手动操作'),
    )

    id = models.AutoField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="名称")
    sn_code = models.CharField(max_length=255, null=True, blank=True, verbose_name="SN码")
    material_code = models.CharField(max_length=255, null=True, blank=True, verbose_name="物料编码")
    # 产品型号：仅成品管理(module=finish_product)来源的记录保存，其他来源无此字段则留空
    product_model = models.CharField(max_length=255, null=True, blank=True, verbose_name="产品型号")
    storage_status = models.IntegerField(choices=STORAGE_CHOICES, verbose_name="操作类型")
    count = models.IntegerField(default=1, verbose_name="数量")
    description = models.TextField(null=True, blank=True, verbose_name="操作描述")
    user_description = models.TextField(null=True, blank=True, verbose_name="用户描述")

    # 新增字段：操作人
    operator_id = models.BigIntegerField(null=True, blank=True, verbose_name="操作人ID")
    operator_name = models.CharField(max_length=64, null=True, blank=True, verbose_name="操作人昵称")
    
    # 新增字段：操作来源模块
    module = models.CharField(max_length=32, choices=MODULE_CHOICES, null=True, blank=True, verbose_name="操作来源模块")
    
    # 新增字段：操作详情（JSON格式，记录对数据的所有操作）
    operation_detail = models.JSONField(null=True, blank=True, verbose_name="操作详情")
    
    # 新增字段：操作类型（更细粒度的操作类型）
    action_type = models.CharField(max_length=32, null=True, blank=True, verbose_name="具体操作类型")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'warehouse_log'
        verbose_name = "库存操作日志"
        verbose_name_plural = "库存操作日志管理"
        ordering = ['-created_at']  # 按创建时间倒序排列

    def __str__(self):
        return f"{self.sn_code or self.material_code} - {self.get_storage_status_display()} - {self.operator_name or '系统'}"