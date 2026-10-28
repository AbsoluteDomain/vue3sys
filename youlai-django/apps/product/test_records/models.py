from django.db import models


class TestRecord(models.Model):
    STATUS_PASS = 2
    STATUS_FAIL = 3
    STATUS_CHOICES = (
        (STATUS_PASS, "测试合格"),
        (STATUS_FAIL, "测试不良"),
    )

    id = models.AutoField(primary_key=True, verbose_name="ID")
    product_id = models.IntegerField(db_index=True, verbose_name="成品ID")
    sn_code = models.CharField(max_length=100, blank=True, default="", verbose_name="成品SN码")
    product_model = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="产品型号",
        help_text="测试时从成品关联BOM同步",
    )
    unqualified_values = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="不良项值",
        help_text="测试不良时选择的字典 unqualified_status 值快照，逗号分隔",
    )
    test_desc = models.TextField(
        blank=True,
        default="",
        verbose_name="测试描述",
        help_text="测试时填写的补充描述",
    )
    test_status = models.IntegerField(
        db_index=True,
        choices=STATUS_CHOICES,
        verbose_name="测试状态",
        help_text="2=测试合格，3=测试不良",
    )
    test_cnt = models.IntegerField(
        default=1,
        verbose_name="测试次数",
        help_text="同一成品SN码下的测试序号，从1开始",
    )
    is_del = models.IntegerField(default=0, verbose_name="删除标记")
    create_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="测试时间")

    class Meta:
        db_table = "test_record"
        verbose_name = "测试记录"
        verbose_name_plural = "测试记录"
