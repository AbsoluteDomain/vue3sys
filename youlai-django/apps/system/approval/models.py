"""系统管理-审批配置模型。

"""
from django.db import models


class ApprovalConfig(models.Model):
    """
    表名：approval_config
    表说明：审批配置表，记录需要进行审批的业务功能及其审核人、审批模式与启用状态。
    """

    biz_type = models.CharField(
        max_length=32, unique=True, verbose_name="业务类型", help_text="业务类型编码（如 inbound 入库、outbound 出库）"
    )
    perm_code = models.CharField(
        max_length=128, unique=True, blank=True, default="", verbose_name="权限标识",
        help_text="权限标识（按钮权限编码，如 product:stock:inbound）",
    )
    menu_id = models.BigIntegerField(
        null=True, blank=True, verbose_name="菜单ID", help_text="按钮权限对应的菜单ID"
    )
    name = models.CharField(max_length=64, verbose_name="功能名称", help_text="功能名称（如入库、出库）")
    enabled = models.SmallIntegerField(
        default=0, verbose_name="审核状态", help_text="审核状态（1-已启用, 0-未启用）"
    )
    approval_mode = models.CharField(
        max_length=16, default="single", verbose_name="审批模式",
        help_text="审批模式（single-单人审批/或签, multi-多人审批/会签）",
    )
    approver_ids = models.CharField(
        max_length=500, blank=True, default="", verbose_name="审核人ID",
        help_text="审核人ID列表（英文逗号分隔）",
    )
    approver_names = models.CharField(
        max_length=500, blank=True, default="", verbose_name="审核人名称",
        help_text="审核人名称列表（英文逗号分隔）",
    )
    editor_id = models.BigIntegerField(null=True, blank=True, verbose_name="最近修改人ID", help_text="最近修改人ID")
    editor_name = models.CharField(
        max_length=64, blank=True, null=True, verbose_name="最近修改人", help_text="最近修改人名称"
    )
    created_at = models.DateTimeField(null=True, blank=True, verbose_name="创建时间", help_text="创建时间")
    updated_at = models.DateTimeField(null=True, blank=True, verbose_name="更新时间", help_text="更新时间")

    class Meta:
        db_table = "approval_config"
        verbose_name = "审批配置"
        verbose_name_plural = "审批配置"


class ApprovalRequest(models.Model):
    """
    表名：approval_request
    表说明：审批申请单表，记录用户提交的待审批业务操作及其执行结果。
    """

    STATUS_PENDING = 0
    STATUS_APPROVED = 1
    STATUS_REJECTED = 2
    STATUS_FAILED = 3

    biz_type = models.CharField(
        max_length=32, verbose_name="业务类型", help_text="业务类型编码（如 inbound 入库、outbound 出库）"
    )
    name = models.CharField(max_length=64, verbose_name="功能名称", help_text="功能名称（如入库、出库）")
    target_id = models.BigIntegerField(verbose_name="业务对象ID", help_text="业务对象ID（如产品ID）")
    target_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="业务对象名称", help_text="业务对象名称（如产品名称）"
    )
    summary = models.CharField(
        max_length=500, blank=True, default="", verbose_name="申请内容", help_text="申请内容摘要"
    )
    payload = models.TextField(
        blank=True, default="", verbose_name="业务参数", help_text="业务参数（JSON 文本，审批通过后据此执行业务）"
    )
    applicant_id = models.BigIntegerField(null=True, blank=True, verbose_name="申请人ID", help_text="申请人ID")
    applicant_name = models.CharField(
        max_length=64, blank=True, default="", verbose_name="申请人", help_text="申请人名称"
    )
    approval_mode = models.CharField(
        max_length=16, default="single", verbose_name="审批模式",
        help_text="审批模式（single-单人审批/或签, multi-多人审批/会签）",
    )
    status = models.SmallIntegerField(
        default=STATUS_PENDING, verbose_name="审批状态",
        help_text="审批状态（0-待审批, 1-已通过, 2-已驳回, 3-执行失败）",
    )
    execute_error = models.CharField(
        max_length=500, blank=True, default="", verbose_name="执行失败原因", help_text="执行失败原因"
    )
    created_at = models.DateTimeField(null=True, blank=True, verbose_name="提交时间", help_text="提交时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间", help_text="审批完成时间")

    class Meta:
        db_table = "approval_request"
        verbose_name = "审批申请"
        verbose_name_plural = "审批申请"


class ApprovalRequestApprover(models.Model):
    """
    表名：approval_request_approver
    表说明：审批申请的审核人明细表，记录每位审核人的处理状态与意见。
    """

    DECISION_PENDING = 0
    DECISION_APPROVED = 1
    DECISION_REJECTED = 2

    request = models.ForeignKey(
        ApprovalRequest, on_delete=models.CASCADE, related_name="approvers",
        verbose_name="审批申请ID", help_text="审批申请ID",
    )
    approver_id = models.BigIntegerField(verbose_name="审核人ID", help_text="审核人ID")
    approver_name = models.CharField(max_length=64, blank=True, default="", verbose_name="审核人", help_text="审核人名称")
    decision = models.SmallIntegerField(
        default=DECISION_PENDING, verbose_name="审批结果",
        help_text="审批结果（0-待处理, 1-同意, 2-拒绝）",
    )
    comment = models.CharField(max_length=500, blank=True, default="", verbose_name="审批意见", help_text="审批意见")
    decided_at = models.DateTimeField(null=True, blank=True, verbose_name="处理时间", help_text="处理时间")

    class Meta:
        db_table = "approval_request_approver"
        verbose_name = "审批申请审核人"
        verbose_name_plural = "审批申请审核人"
