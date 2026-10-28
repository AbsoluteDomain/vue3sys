from django.db import models


class FinishProduct(models.Model):
    """成品表：BOM 组装成功后生成的成品记录"""

    STATUS_UNTESTED = 0
    STATUS_TESTING = 1
    STATUS_PASS = 2
    STATUS_FAIL = 3
    STATUS_UNASSEMBLED = 4
    STATUS_CHOICES = (
        (STATUS_UNTESTED, "未测试"),
        (STATUS_TESTING, "测试中"),
        (STATUS_PASS, "测试合格"),
        (STATUS_FAIL, "测试不良"),
        (STATUS_UNASSEMBLED, "未组装"),
    )

    INVENTORY_NOT_IN = 0
    INVENTORY_IN = 1
    INVENTORY_OUT_SALE = 2
    INVENTORY_OUT_DEV = 3
    INVENTORY_CONSUME = 4
    INVENTORY_OUT_SCRAP = 5
    INVENTORY_OUT_EXCHANGE = 6
    INVENTORY_STOCK_CHOICES = (
        (INVENTORY_NOT_IN, "未入库"),
        (INVENTORY_IN, "入库"),
        (INVENTORY_OUT_SALE, "出库（外销）"),
        (INVENTORY_OUT_DEV, "出库（研发）"),
        (INVENTORY_CONSUME, "组件消耗"),
        (INVENTORY_OUT_SCRAP, "出库（报废）"),
        (INVENTORY_OUT_EXCHANGE, "出库（换货）"),
    )

    REPAIR_NEW = 0
    REPAIR_REPAIRED = 1
    REPAIR_CHOICES = (
        (REPAIR_NEW, "新品"),
        (REPAIR_REPAIRED, "返修品"),
    )

    CONS_STATUS_CONSUMED = 0
    CONS_STATUS_NOT_CONSUMED = 1
    CONS_STATUS_ROLLED_BACK = 2
    CONS_STATUS_CHOICES = (
        (CONS_STATUS_CONSUMED, "已扣料"),
        (CONS_STATUS_NOT_CONSUMED, "未扣料"),
        (CONS_STATUS_ROLLED_BACK, "已回退"),
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
    sn_code_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="SN码录入时间",
        help_text="SN码发生变化时由系统自动写入，不可编辑",
    )
    sn_code_binder = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="SN码绑定人",
        help_text="SN码发生变化时由系统自动写入当前操作人，不可编辑",
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
    parent_sn_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="父级SN码",
        help_text="记录该成品所属的父级产品SN码",
    )
    cons_status = models.IntegerField(
        choices=CONS_STATUS_CHOICES,
        blank=True,
        null=True,
        verbose_name="物料消耗状态",
        help_text="0=组装已扣料 1=组装未扣料 2=已回退（回退不删除记录）；NULL=历史数据",
    )
    creator_id = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="创建人ID",
        help_text="创建该成品时的操作用户ID",
    )
    creator_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="创建人",
        help_text="创建该成品时的操作用户姓名（昵称优先，无昵称取用户名）",
    )
    editor_id = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="最后操作人ID",
        help_text="最后一次修改该成品的操作用户ID",
    )
    editor_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="最后操作人",
        help_text="最后一次修改该成品的操作用户姓名（昵称优先，无昵称取用户名）",
    )

    class Meta:
        db_table = "finish_product"
        verbose_name = "成品"
        verbose_name_plural = "成品"
        ordering = ["-create_time", "-id"]

    @classmethod
    def active_queryset(cls):
        """排除已回退（cons_status=2）的记录，用于列表/统计/绑定等业务查询"""
        return cls.objects.exclude(cons_status=cls.CONS_STATUS_ROLLED_BACK)

    def __str__(self):
        return self.sn_code or f"{self.name}#{self.id}"


class UnqualifiedItem(models.Model):
    """成品不合格项表：存储成品与不合格项字典的绑定关系"""

    id = models.AutoField(primary_key=True, verbose_name="ID")
    finish_product_id = models.IntegerField(verbose_name="成品ID")
    sn_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="SN码",
    )
    unqualified_value = models.IntegerField(
        verbose_name="不良项值",
        help_text="对应字典 unqualified_status 中的字典项值",
    )
    create_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        db_table = "unqualified_item"
        verbose_name = "成品不合格项"
        verbose_name_plural = "成品不合格项"
        ordering = ["-create_time"]

    def __str__(self):
        return f"{self.sn_code or self.finish_product_id} - {self.unqualified_value}"


class FinishedProductLog(models.Model):
    """成品操作记录表：追踪成品所有列展示字段的前后变更"""

    OPERATION_CREATE = "create"
    OPERATION_UPDATE = "update"
    OPERATION_ROLLBACK = "rollback"
    OPERATION_BIND_JOINT = "bind_joint"
    OPERATION_STOCK_CHANGE = "stock_change"
    OPERATION_UNQUALIFIED = "unqualified"
    OPERATION_CHOICES = (
        (OPERATION_CREATE, "新增"),
        (OPERATION_UPDATE, "修改"),
        (OPERATION_ROLLBACK, "回退"),
        (OPERATION_BIND_JOINT, "绑定关节"),
        (OPERATION_STOCK_CHANGE, "库存变更"),
        (OPERATION_UNQUALIFIED, "不良详情"),
    )

    # 列展示字段白名单（与前端 useFinishProductTableColumns 一致）
    TRACKABLE_FIELDS = (
        "sn_code", "sn_code_time", "bom_type", "bom_model", "bom_name", "material_code",
        "parent_sn_code", "status", "inventory_stock", "repair",
        "test_time", "stock_in_time", "stock_out_time",
        "create_time", "update_time", "description",
    )

    id = models.AutoField(primary_key=True, verbose_name="主键ID")
    finish_product_id = models.BigIntegerField(
        null=True, blank=True, verbose_name="成品ID"
    )
    sn_code = models.CharField(
        max_length=255, blank=True, default="", verbose_name="SN码"
    )
    operation_type = models.CharField(
        max_length=20, choices=OPERATION_CHOICES, verbose_name="操作类型"
    )
    operator_id = models.BigIntegerField(
        null=True, blank=True, verbose_name="操作人ID"
    )
    operator_name = models.CharField(
        max_length=100, blank=True, default="", verbose_name="操作人姓名"
    )
    before_data = models.JSONField(
        null=True, blank=True, verbose_name="变更前数据快照"
    )
    after_data = models.JSONField(
        null=True, blank=True, verbose_name="变更后数据快照"
    )
    changed_fields = models.JSONField(
        default=list, blank=True, verbose_name="变更字段列表"
    )
    description = models.CharField(
        max_length=500, blank=True, default="", verbose_name="操作描述"
    )
    ip = models.CharField(
        max_length=45, blank=True, null=True, verbose_name="IP地址"
    )
    create_time = models.DateTimeField(
        auto_now_add=True, verbose_name="记录时间"
    )

    class Meta:
        db_table = "finished_product_log"
        verbose_name = "成品操作记录"
        verbose_name_plural = "成品操作记录"
        ordering = ["-create_time", "-id"]

    def __str__(self):
        return f"{self.sn_code or self.finish_product_id} - {self.get_operation_type_display()}"
