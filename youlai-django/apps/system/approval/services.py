"""系统管理-审批流转服务。

提供审批申请单的创建、查询、审批决策与业务执行能力。
"""
import json
import logging

from django.db import transaction
from django.utils import timezone

from apps.system.operation_logs.request_user import get_request_operator
from apps.system.users.models import User

from .models import ApprovalConfig, ApprovalRequest, ApprovalRequestApprover

logger = logging.getLogger(__name__)

STATUS_NAMES = {0: "待审批", 1: "已通过", 2: "已驳回", 3: "执行失败"}
DECISION_NAMES = {0: "待处理", 1: "同意", 2: "拒绝"}
APPROVAL_MODES = {"single": "单人审批", "multi": "多人审批"}
BIZ_ACTIONS = {"inbound": "入库", "outbound": "出库"}


def get_active_config(biz_type: str):
    """获取已启用的业务审批配置，未启用返回 None。"""
    return ApprovalConfig.objects.filter(biz_type=biz_type, enabled=1).first()


def get_active_config_by_perm(perm_code: str):
    """按权限标识获取已启用的审批配置，未启用返回 None。"""
    return ApprovalConfig.objects.filter(perm_code=perm_code, enabled=1).first()


def resolve_approvers(config: ApprovalConfig):
    """解析配置中的有效审核人，返回 (审核人ID列表, {ID: 名称})。"""
    approver_ids = _config_approver_ids(config)
    user_map = {
        user.id: (user.nickname or user.username or "")
        for user in User.objects.filter(id__in=approver_ids, is_deleted=0)
    }
    return [uid for uid in approver_ids if uid in user_map], user_map


def create_approval_request(
    request,
    config: ApprovalConfig,
    perm_code: str,
    target_id,
    target_name,
    summary,
    steps,
):
    """创建审批申请单。

    Args:
        steps: 审批通过后需要重放执行的业务请求列表，形如
            [{"path": "/api/v1/...", "method": "POST", "body": {...}}]
    Returns:
        ApprovalRequest；审核人无效时返回 None（调用方按普通流程执行）。
    """
    valid_ids, user_map = resolve_approvers(config)
    if not valid_ids:
        return None

    operator = get_request_operator(request)
    applicant_id, applicant_name = operator if operator else (None, "")

    payload = json.dumps({"perm_code": perm_code, "steps": steps}, ensure_ascii=False)
    now = timezone.now()
    # target_id 用于展示与追溯，新增类业务提交时可能还没有业务主键，统一存 0
    target_id = target_id or 0
    with transaction.atomic():
        approval_request = ApprovalRequest.objects.create(
            biz_type=config.biz_type,
            name=config.name,
            target_id=target_id,
            target_name=(target_name or "")[:255],
            summary=(summary or "")[:500],
            payload=payload,
            applicant_id=applicant_id,
            applicant_name=applicant_name or "",
            approval_mode=config.approval_mode,
            status=ApprovalRequest.STATUS_PENDING,
            created_at=now,
        )
        ApprovalRequestApprover.objects.bulk_create(
            [
                ApprovalRequestApprover(
                    request=approval_request,
                    approver_id=uid,
                    approver_name=user_map[uid],
                )
                for uid in valid_ids
            ]
        )

    return approval_request


def maybe_submit_approval(
    request,
    perm_code,
    allowed_perms,
    target_id,
    target_name,
    summary=None,
):
    """业务接口通用审批拦截。

    前端在请求体中通过 approval_perm 指明当前按钮对应的权限，后端校验该权限
    在 allowed_perms 白名单内且审批已启用时，创建审批申请单并暂停业务执行。

    Returns:
        ApprovalRequest 或 None（未启用审批时返回 None，调用方继续原业务）
    """
    if not perm_code or perm_code not in allowed_perms:
        return None
    if getattr(request, "_approval_bypass", False):
        return None
    config = get_active_config_by_perm(perm_code)
    if not config:
        return None
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        body = {}
    summary = summary or f"{config.name}：{target_name or target_id or ''}"
    steps = [{"path": request.path, "method": request.method, "body": body}]
    return create_approval_request(
        request, config, perm_code, target_id, target_name, summary, steps
    )


def pending_response(approval_request):
    """构造「已提交审批」的统一响应。"""
    from django.http import JsonResponse

    return JsonResponse(
        {
            "code": "00000",
            "msg": "已提交审批，等待审核",
            "data": {"pending": True, "request_id": approval_request.id},
        }
    )


def _config_approver_ids(config: ApprovalConfig):
    return [int(i) for i in (config.approver_ids or "").split(",") if i.strip().isdigit()]


def submit_stock_request(request, config, product, adjust_type, delta, storage_status, user_description):
    """为出入库操作创建审批申请单。

    Returns:
        ApprovalRequest 实例；配置未正确设置审核人时返回 None（调用方按普通流程执行）。
    """
    approver_ids = _config_approver_ids(config)
    if not approver_ids:
        return None

    operator = get_request_operator(request)
    applicant_id, applicant_name = operator if operator else (None, "")

    user_map = {
        user.id: (user.nickname or user.username or "")
        for user in User.objects.filter(id__in=approver_ids, is_deleted=0)
    }
    valid_ids = [uid for uid in approver_ids if uid in user_map]
    if not valid_ids:
        return None

    action = BIZ_ACTIONS.get(config.biz_type, config.name)
    current = product.quantity if product.quantity is not None else 0
    summary = f"{action} {delta} {product.unit or ''}（当前库存 {current}）".replace("  ", " ").strip()

    payload = json.dumps(
        {
            "type": adjust_type,
            "quantity": delta,
            "storage_status": storage_status,
            "user_description": user_description or "",
        },
        ensure_ascii=False,
    )

    now = timezone.now()
    with transaction.atomic():
        approval_request = ApprovalRequest.objects.create(
            biz_type=config.biz_type,
            name=config.name,
            target_id=product.id,
            target_name=product.name or "",
            summary=summary,
            payload=payload,
            applicant_id=applicant_id,
            applicant_name=applicant_name or "",
            approval_mode=config.approval_mode,
            status=ApprovalRequest.STATUS_PENDING,
            created_at=now,
        )
        ApprovalRequestApprover.objects.bulk_create(
            [
                ApprovalRequestApprover(
                    request=approval_request,
                    approver_id=uid,
                    approver_name=user_map[uid],
                )
                for uid in valid_ids
            ]
        )

    return approval_request


def pending_count(user_id):
    """当前用户待处理的审批数量。"""
    if not user_id:
        return 0
    return (
        ApprovalRequest.objects.filter(
            status=ApprovalRequest.STATUS_PENDING,
            approvers__approver_id=user_id,
            approvers__decision=ApprovalRequestApprover.DECISION_PENDING,
        )
        .distinct()
        .count()
    )


def pending_queryset(user_id):
    """当前用户待处理的审批申请。"""
    if not user_id:
        return ApprovalRequest.objects.none()
    return ApprovalRequest.objects.filter(
        status=ApprovalRequest.STATUS_PENDING,
        approvers__approver_id=user_id,
        approvers__decision=ApprovalRequestApprover.DECISION_PENDING,
    ).distinct()


def my_applied_queryset(user_id):
    """当前用户发起的审批申请。"""
    if not user_id:
        return ApprovalRequest.objects.none()
    return ApprovalRequest.objects.filter(applicant_id=user_id)


def my_decided_queryset(user_id):
    """当前用户已处理过的审批申请（同意或拒绝）。"""
    if not user_id:
        return ApprovalRequest.objects.none()
    return ApprovalRequest.objects.filter(
        approvers__approver_id=user_id,
        approvers__decision__in=[
            ApprovalRequestApprover.DECISION_APPROVED,
            ApprovalRequestApprover.DECISION_REJECTED,
        ],
    ).distinct()


def _format_time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def build_request_events(approval_request: ApprovalRequest) -> list:
    """构建单个审批申请单的完整历史时间线。

    依次包含：提交审批、各审核人同意/拒绝、审批通过后的业务执行结果。
    """
    events = [
        {
            "type": "submit",
            "type_name": "提交审批",
            "actor": approval_request.applicant_name or "",
            "detail": approval_request.summary or "",
            "time": _format_time(approval_request.created_at),
        }
    ]

    for approver in approval_request.approvers.all().order_by("decided_at", "id"):
        if approver.decision == ApprovalRequestApprover.DECISION_PENDING:
            continue
        events.append(
            {
                "type": "approve" if approver.decision == ApprovalRequestApprover.DECISION_APPROVED else "reject",
                "type_name": DECISION_NAMES.get(approver.decision, "处理"),
                "actor": approver.approver_name or "",
                "detail": approver.comment or "",
                "time": _format_time(approver.decided_at),
            }
        )

    if approval_request.status in (
        ApprovalRequest.STATUS_APPROVED,
        ApprovalRequest.STATUS_FAILED,
    ):
        events.append(
            {
                "type": "execute_failed" if approval_request.status == ApprovalRequest.STATUS_FAILED else "execute",
                "type_name": (
                    "业务执行失败"
                    if approval_request.status == ApprovalRequest.STATUS_FAILED
                    else "业务执行成功"
                ),
                "actor": "系统",
                "detail": approval_request.execute_error or "",
                "time": _format_time(approval_request.finished_at),
            }
        )

    return events


def serialize_request(approval_request: ApprovalRequest, user_id=None) -> dict:
    approvers = list(approval_request.approvers.all())
    my_approver = next((item for item in approvers if item.approver_id == user_id), None)
    return {
        "id": approval_request.id,
        "biz_type": approval_request.biz_type,
        "name": approval_request.name,
        "target_id": approval_request.target_id,
        "target_name": approval_request.target_name or "",
        "summary": approval_request.summary or "",
        "applicant_id": approval_request.applicant_id,
        "applicant_name": approval_request.applicant_name or "",
        "approval_mode": approval_request.approval_mode,
        "approval_mode_name": APPROVAL_MODES.get(approval_request.approval_mode, "单人审批"),
        "status": approval_request.status,
        "status_name": STATUS_NAMES.get(approval_request.status, "待审批"),
        "execute_error": approval_request.execute_error or "",
        "created_at": (
            approval_request.created_at.strftime("%Y-%m-%d %H:%M:%S") if approval_request.created_at else ""
        ),
        "finished_at": (
            approval_request.finished_at.strftime("%Y-%m-%d %H:%M:%S") if approval_request.finished_at else ""
        ),
        "approvers": [
            {
                "approver_id": item.approver_id,
                "approver_name": item.approver_name or "",
                "decision": item.decision,
                "decision_name": DECISION_NAMES.get(item.decision, "待处理"),
                "comment": item.comment or "",
                "decided_at": item.decided_at.strftime("%Y-%m-%d %H:%M:%S") if item.decided_at else "",
            }
            for item in approvers
        ],
        "my_decision": my_approver.decision if my_approver else None,
        "can_decide": bool(
            approval_request.status == ApprovalRequest.STATUS_PENDING
            and my_approver
            and my_approver.decision == ApprovalRequestApprover.DECISION_PENDING
        ),
    }


def decide_request(request, request_id, decision, comment=""):
    """处理审批：同意或拒绝。

    Returns:
        (ApprovalRequest, 提示信息)

    Raises:
        ValueError: 参数或状态不合法
    """
    operator = get_request_operator(request)
    if not operator:
        raise ValueError("无法识别当前操作人，请重新登录后再试")
    user_id, _user_name = operator

    with transaction.atomic():
        approval_request = (
            ApprovalRequest.objects.select_for_update().filter(id=request_id).first()
        )
        if not approval_request:
            raise ValueError("审批申请不存在")
        if approval_request.status != ApprovalRequest.STATUS_PENDING:
            raise ValueError("该审批已处理，无需重复操作")

        approver = approval_request.approvers.filter(
            approver_id=user_id, decision=ApprovalRequestApprover.DECISION_PENDING
        ).first()
        if not approver:
            raise ValueError("您不是该审批的待处理审核人")

        now = timezone.now()
        approver.decision = decision
        approver.comment = (comment or "")[:500]
        approver.decided_at = now
        approver.save(update_fields=["decision", "comment", "decided_at"])

        if decision == ApprovalRequestApprover.DECISION_REJECTED:
            approval_request.status = ApprovalRequest.STATUS_REJECTED
            approval_request.finished_at = now
            approval_request.save(update_fields=["status", "finished_at"])
            return approval_request, "已驳回该审批"

        # 同意：单人审批直接通过；多人审批需全部审核人同意
        if approval_request.approval_mode == "multi":
            remaining = approval_request.approvers.filter(
                decision=ApprovalRequestApprover.DECISION_PENDING
            ).count()
            if remaining > 0:
                return approval_request, f"已同意，等待其他审核人处理（剩余 {remaining} 人）"

        approval_request.status = ApprovalRequest.STATUS_APPROVED
        approval_request.finished_at = now
        approval_request.save(update_fields=["status", "finished_at"])

        executed, error = _execute_request(approval_request, request)
        if not executed:
            return approval_request, f"审批已通过，但业务执行失败：{error}"
        return approval_request, "审批已通过，业务已执行"


def _execute_request(approval_request, request):
    """审批通过后执行原始业务操作，失败时记录原因。

    Returns:
        (是否执行成功, 失败原因)
    """
    try:
        payload = json.loads(approval_request.payload or "{}")
        steps = payload.get("steps")
        if steps:
            _replay_steps(approval_request, steps)
        else:
            from apps.product.products.views import apply_stock_adjust

            apply_stock_adjust(
                product_id=approval_request.target_id,
                adjust_type=payload.get("type"),
                delta=int(payload.get("quantity") or 0),
                request=request,
                storage_status=payload.get("storage_status"),
                user_description=payload.get("user_description") or "",
                write_warehouse_log=True,
            )
        return True, ""
    except Exception as exc:  # noqa: BLE001 - 执行失败需落库记录，不能中断审批流程
        logger.error("审批业务执行失败 request_id=%s: %s", approval_request.id, exc, exc_info=True)
        approval_request.status = ApprovalRequest.STATUS_FAILED
        approval_request.execute_error = str(exc)[:500]
        approval_request.finished_at = timezone.now()
        approval_request.save(update_fields=["status", "execute_error", "finished_at"])
        return False, str(exc)


def _replay_steps(approval_request, steps):
    """按申请人身份重放业务请求，执行审批通过后的业务操作。"""
    from django.test import RequestFactory
    from django.urls import resolve

    applicant = User.objects.filter(id=approval_request.applicant_id).first()
    factory = RequestFactory()

    for step in steps:
        path = (step.get("path") or "").strip()
        if not path:
            raise ValueError("审批执行参数缺少请求地址")
        method = (step.get("method") or "POST").upper()
        body = step.get("body") or {}

        if method == "GET":
            replay = factory.get(path, data=body)
        else:
            replay = factory.generic(
                method,
                path,
                data=json.dumps(body, ensure_ascii=False),
                content_type="application/json",
            )
        # 标记为重放请求，避免再次触发审批拦截
        replay._approval_bypass = True
        if applicant:
            replay.user = applicant
            replay.META["_JWT_PAYLOAD"] = {
                "user_id": applicant.id,
                "user_name": applicant.username,
                "nickname": applicant.nickname or applicant.username,
            }

        match = resolve(path)
        response = match.func(replay, *match.args, **match.kwargs)
        try:
            data = json.loads((getattr(response, "content", b"{}") or b"{}").decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            data = {}

        if getattr(response, "status_code", 200) >= 400 or data.get("code") != "00000":
            raise ValueError(data.get("msg") or "业务执行失败")
