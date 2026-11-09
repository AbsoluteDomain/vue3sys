"""系统管理-审批配置视图。

"""
import json

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.system.menus.models import Menu
from apps.system.operation_logs.request_user import get_request_operator
from apps.system.users.models import User
from core.pagination import parse_page_params

from . import services
from .models import ApprovalConfig, ApprovalRequest, ApprovalRequestApprover

APPROVAL_MODES = {"single": "单人审批", "multi": "多人审批"}

# 审核管理展示范围：产品管理下的这些模块
APPROVAL_ROOT_ROUTE = "/product"
APPROVAL_MODULE_NAMES = ["成品管理", "库存管理", "生产计划", "产品BOM管理", "返修管理"]
# 不纳入审核的权限（URDF 展示仅作查看，无业务操作）
APPROVAL_EXCLUDED_PERMS = {"product:bom:urdf"}

# 通用审批提交接口允许重放的业务地址（防止越权提交任意请求）
PERM_ALLOWED_PATHS = {
    "product:stock:create": ["/api/v1/product/create/"],
    "product:stock:update": ["/api/v1/product/update/"],
    "product:stock:delete": ["/api/v1/product/delete/"],
    "product:finish:assemble": ["/api/v1/bom/assemble/"],
    "product:finish:add-joint": ["/api/v1/finish-product/create/"],
    "product:finish:update": ["/api/v1/finish-product/update/"],
    "product:finish:test-pass": ["/api/v1/finish-product/update/"],
    "product:finish:test-fail": ["/api/v1/finish-product/update/"],
    "product:finish:batch-sn": ["/api/v1/finish-product/update/"],
    "product:finish:rollback": ["/api/v1/finish-product/rollback/"],
    "product:finish:bind": ["/api/v1/finish-product/bind-joints/"],
    "production:plan:save": ["/api/v1/production-plan/save"],
    "product:bom:create": ["/api/v1/bom/create/", "/api/v1/bom/import/"],
    "product:bom:update": ["/api/v1/bom/update/"],
    "product:bom:delete": ["/api/v1/bom/delete/"],
    "product:repair:save": ["/api/v1/repair/create/"],
    "product:repair:delete": ["/api/v1/repair/delete/"],
}


def _ok(data=None, msg="成功"):
    return JsonResponse({"code": "00000", "msg": msg, "data": data})


def _error(msg, code="A0400", status=400):
    return JsonResponse({"code": code, "msg": msg, "data": None}, status=status)


def _parse_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def _serialize(config: ApprovalConfig) -> dict:
    approver_ids = [int(i) for i in (config.approver_ids or "").split(",") if i.strip().isdigit()]
    return {
        "id": config.id,
        "biz_type": config.biz_type,
        "perm_code": config.perm_code or "",
        "menu_id": config.menu_id,
        "row_key": f"config-{config.id}",
        "node_type": "button",
        "name": config.name,
        "enabled": config.enabled,
        "approval_mode": config.approval_mode,
        "approval_mode_name": APPROVAL_MODES.get(config.approval_mode, "单人审批"),
        "approver_ids": approver_ids,
        "approver_names": config.approver_names or "",
        "editor_name": config.editor_name or "",
        "updated_at": config.updated_at.strftime("%Y-%m-%d %H:%M:%S") if config.updated_at else "",
    }


def _button_node(config: ApprovalConfig, button: Menu) -> dict:
    node = _serialize(config)
    node["menu_id"] = button.id
    node["name"] = config.name or button.name
    node["perm_code"] = button.perm or config.perm_code or ""
    return node


def _build_config_tree():
    """按产品管理->模块->按钮权限三级结构组装审核配置树。"""
    root_menu = Menu.objects.filter(parent_id=0, route_path=APPROVAL_ROOT_ROUTE).first()
    if not root_menu:
        # 找不到菜单结构时退化为平铺列表，保证配置仍可维护
        return [_serialize(config) for config in ApprovalConfig.objects.all().order_by("id")]

    config_map = {config.perm_code: config for config in ApprovalConfig.objects.all() if config.perm_code}
    modules = Menu.objects.filter(
        parent_id=root_menu.id, name__in=APPROVAL_MODULE_NAMES, type="M"
    ).order_by("sort", "id")

    module_nodes = []
    for module in modules:
        buttons = (
            Menu.objects.filter(parent_id=module.id, type="B")
            .exclude(perm__isnull=True)
            .exclude(perm="")
            .exclude(perm__in=APPROVAL_EXCLUDED_PERMS)
            .order_by("sort", "id")
        )
        children = []
        for button in buttons:
            config = config_map.get(button.perm)
            if config:
                children.append(_button_node(config, button))
            else:
                children.append(
                    {
                        "id": None,
                        "biz_type": "",
                        "perm_code": button.perm,
                        "menu_id": button.id,
                        "row_key": f"menu-{button.id}",
                        "node_type": "button",
                        "name": button.name,
                        "enabled": 0,
                        "approval_mode": "single",
                        "approval_mode_name": "单人审批",
                        "approver_ids": [],
                        "approver_names": "",
                        "editor_name": "",
                        "updated_at": "",
                    }
                )

        module_nodes.append(
            {
                "id": None,
                "perm_code": module.perm or "",
                "menu_id": module.id,
                "row_key": f"menu-{module.id}",
                "node_type": "menu",
                "name": module.name,
                "enabled_count": sum(1 for child in children if child["enabled"]),
                "total": len(children),
                "children": children,
            }
        )

    return [
        {
            "id": None,
            "perm_code": "",
            "menu_id": root_menu.id,
            "row_key": f"menu-{root_menu.id}",
            "node_type": "catalog",
            "name": root_menu.name,
            "enabled_count": sum(node["enabled_count"] for node in module_nodes),
            "total": sum(node["total"] for node in module_nodes),
            "children": module_nodes,
        }
    ]


@require_http_methods(["GET"])
def config_list(request):
    """查询所有需要审核的业务功能配置（产品管理->模块->权限三级结构）。"""
    return _ok(_build_config_tree())


def _parse_config_form(body, config=None):
    """校验审核配置表单，返回 (错误消息, 清洗后的数据)。"""
    enabled = body.get("enabled", config.enabled if config else 0)
    try:
        enabled = int(enabled)
    except (TypeError, ValueError):
        return "审核状态参数不正确", None
    if enabled not in (0, 1):
        return "审核状态参数不正确", None

    approval_mode = body.get("approval_mode", config.approval_mode if config else "single")
    if approval_mode not in APPROVAL_MODES:
        return "审批模式参数不正确", None

    raw_ids = body.get("approver_ids", [])
    if not isinstance(raw_ids, list):
        return "审核人参数不正确", None
    approver_ids = []
    for item in raw_ids:
        try:
            approver_ids.append(int(item))
        except (TypeError, ValueError):
            return "审核人参数不正确", None

    users = User.objects.filter(id__in=approver_ids, is_deleted=0)
    user_map = {user.id: (user.nickname or user.username) for user in users}
    missing_ids = [str(i) for i in approver_ids if i not in user_map]
    if missing_ids:
        return f"审核人不存在：{','.join(missing_ids)}", None

    if enabled == 1 and not approver_ids:
        return "启用审核时必须至少选择一名审核人", None

    return None, {
        "enabled": enabled,
        "approval_mode": approval_mode,
        "approver_ids": approver_ids,
        "user_map": user_map,
    }


def _apply_config(config, values, request):
    """将校验后的表单值写入配置对象并保存。"""
    operator = get_request_operator(request)
    user_id, user_name = operator if operator else (None, "")

    config.enabled = values["enabled"]
    config.approval_mode = values["approval_mode"]
    config.approver_ids = ",".join(str(i) for i in values["approver_ids"])
    config.approver_names = ",".join(values["user_map"][i] for i in values["approver_ids"])
    config.editor_id = user_id
    config.editor_name = user_name or ""
    config.updated_at = timezone.now()
    config.save()
    return config


@csrf_exempt
@require_http_methods(["POST"])
def config_create(request):
    """首次保存按钮权限的审核配置（配置行尚不存在时创建）。"""
    body = _parse_body(request)
    perm_code = (body.get("perm_code") or "").strip()
    if not perm_code:
        return _error("权限标识不能为空")

    try:
        menu_id = int(body.get("menu_id"))
    except (TypeError, ValueError):
        return _error("权限项参数不正确")

    button = Menu.objects.filter(id=menu_id, type="B").first()
    if not button or (button.perm or "") != perm_code:
        return _error("权限项不存在或权限标识不匹配")

    name = (body.get("name") or button.name or "").strip()
    if not name:
        return _error("功能名称不能为空")

    error_msg, values = _parse_config_form(body)
    if error_msg:
        return _error(error_msg)

    config = ApprovalConfig.objects.filter(perm_code=perm_code).first()
    if config:
        config.menu_id = button.id
        config.name = name
    else:
        config = ApprovalConfig(
            perm_code=perm_code,
            # biz_type 唯一；出入库需写成 inbound/outbound 供业务接口匹配
            biz_type=services.BIZ_TYPE_BY_PERM.get(perm_code, perm_code),
            menu_id=button.id,
            name=name,
        )

    _apply_config(config, values, request)
    return _ok(_serialize(config), msg="保存成功")


@csrf_exempt
@require_http_methods(["POST", "PUT"])
def config_update(request, config_id):
    """更新审批配置：审核状态、审批模式、审核人。"""
    config = ApprovalConfig.objects.filter(id=config_id).first()
    if not config:
        return _error("审批配置不存在", code="A0400", status=404)

    error_msg, values = _parse_config_form(_parse_body(request), config)
    if error_msg:
        return _error(error_msg)

    _apply_config(config, values, request)
    return _ok(_serialize(config), msg="保存成功")


@require_http_methods(["GET"])
def enabled_perms(request):
    """返回已启用审批的权限标识列表，供前端判断是否需要走审批。"""
    perms = list(
        ApprovalConfig.objects.filter(enabled=1)
        .exclude(perm_code="")
        .values_list("perm_code", flat=True)
    )
    return _ok({"perms": perms})


@csrf_exempt
@require_http_methods(["POST"])
def submit_request(request):
    """通用审批提交：用于批量操作（一次审批包含多条业务请求）。"""
    body = _parse_body(request)
    perm_code = (body.get("perm_code") or "").strip()
    config = services.get_active_config_by_perm(perm_code)
    if not config:
        return _ok({"pending": False})

    allowed_paths = PERM_ALLOWED_PATHS.get(perm_code) or []
    steps = body.get("steps")
    if not allowed_paths or not isinstance(steps, list) or not steps:
        return _error("审批参数不正确")

    for step in steps:
        path = (step.get("path") or "").split("?", 1)[0]
        if path not in allowed_paths:
            return _error("审批参数不正确")

    approval_request = services.create_approval_request(
        request,
        config,
        perm_code,
        body.get("target_id"),
        body.get("target_name") or "",
        body.get("summary") or "",
        steps,
    )
    if not approval_request:
        return _ok({"pending": False}, msg="未配置有效审核人")
    return _ok({"pending": True, "request_id": approval_request.id}, msg="已提交审批，等待审核")


@require_http_methods(["GET"])
def my_task_count(request):
    """当前用户待处理的审批数量及最新一条申请（用于前端新消息提醒）。"""
    operator = get_request_operator(request)
    user_id = operator[0] if operator else None
    count = services.pending_count(user_id)

    latest = None
    if count:
        latest_request = services.pending_queryset(user_id).order_by("-id").first()
        if latest_request:
            latest = {
                "id": latest_request.id,
                "name": latest_request.name,
                "summary": latest_request.summary or "",
                "applicant_name": latest_request.applicant_name or "",
                "created_at": (
                    latest_request.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if latest_request.created_at
                    else ""
                ),
            }

    return _ok({"count": count, "latest": latest})


@require_http_methods(["GET"])
def my_tasks(request):
    """我的审批列表：scope=pending 待我审批，scope=mine 我发起的。"""
    operator = get_request_operator(request)
    if not operator:
        return _error("无法识别当前用户，请重新登录", code="A0230", status=401)
    user_id = operator[0]

    scope = (request.GET.get("scope") or "pending").strip()
    page_num, page_size = parse_page_params(request)

    if scope == "mine":
        queryset = services.my_applied_queryset(user_id)
    elif scope == "processed":
        queryset = services.my_decided_queryset(user_id)
    else:
        queryset = services.pending_queryset(user_id)
    queryset = queryset.order_by("-id")

    total = queryset.count()
    start = (page_num - 1) * page_size
    page_items = queryset[start:start + page_size]
    data = [services.serialize_request(item, user_id) for item in page_items]

    return _ok(
        {
            "list": data,
            "total": total,
            "pageNum": page_num,
            "pageSize": page_size,
        }
    )


@require_http_methods(["GET"])
def request_history(request, request_id):
    """审批申请单的完整历史：提交、各审核人处理、业务执行结果。"""
    approval_request = ApprovalRequest.objects.filter(id=request_id).first()
    if not approval_request:
        return _error("审批申请不存在", code="A0400", status=404)
    return _ok(
        {
            "id": approval_request.id,
            "name": approval_request.name,
            "target_name": approval_request.target_name or "",
            "summary": approval_request.summary or "",
            "status": approval_request.status,
            "status_name": services.STATUS_NAMES.get(approval_request.status, "待审批"),
            "events": services.build_request_events(approval_request),
        }
    )


def _decide_request(request, request_id, decision):
    body = _parse_body(request)
    comment = (body.get("comment") or "").strip()
    try:
        approval_request, message = services.decide_request(request, request_id, decision, comment)
    except ValueError as exc:
        return _error(str(exc))

    operator = get_request_operator(request)
    user_id = operator[0] if operator else None
    return _ok(services.serialize_request(approval_request, user_id), msg=message)


@csrf_exempt
@require_http_methods(["POST"])
def approve_request(request, request_id):
    """同意审批。"""
    return _decide_request(request, request_id, ApprovalRequestApprover.DECISION_APPROVED)


@csrf_exempt
@require_http_methods(["POST"])
def reject_request(request, request_id):
    """拒绝审批。"""
    return _decide_request(request, request_id, ApprovalRequestApprover.DECISION_REJECTED)
