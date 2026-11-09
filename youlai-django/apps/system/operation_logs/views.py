from datetime import datetime

from django.http import JsonResponse
from django.db.models import Q

from core.datetime import format_local_datetime
from .models import OperationLog
from .services import MODULE_DISPLAY_NAMES


def get_module_name(module):
    """获取模块显示名称"""
    return MODULE_DISPLAY_NAMES.get(module, module)


def operation_log_list(request):
    from core.pagination import parse_page_params
    page_num, page_size = parse_page_params(request)

    module = request.GET.get("module", "").strip()
    operation_type = request.GET.get("operationType", "").strip()
    user_name = request.GET.get("userName", "").strip()
    
    logs = OperationLog.objects.all().order_by("-create_time")
    
    if module == "bom":
        logs = logs.filter(module__in=["bom", "productBom"])
    elif module == "product":
        logs = logs.filter(module__in=["product", "productStock"])
    elif module == "finishProduct":
        logs = logs.filter(module="finishProduct")
    elif module:
        logs = logs.filter(module=module)
    if operation_type:
        logs = logs.filter(operation_type=operation_type)
    if user_name:
        logs = logs.filter(user_name__icontains=user_name)
    
    total = logs.count()
    start_idx = (page_num - 1) * page_size
    end_idx = start_idx + page_size
    page_logs = logs[start_idx:end_idx]
    
    list_data = []
    for log in page_logs:
        item = {
            "id": log.id,
            "userId": log.user_id,
            "userName": log.user_name,
            "module": log.module,
            "moduleName": log.module_name or get_module_name(log.module),
            "operationType": log.operation_type,
            "operationTypeName": log.get_operation_type_display(),
            "targetId": log.target_id,
            "targetName": log.target_name,
            "description": log.description,
            "ip": log.ip,
        }
        item["createTime"] = format_local_datetime(log.create_time) or ""
        
        list_data.append(item)
    
    return JsonResponse({
        "code": "00000",
        "data": {
            "list": list_data,
            "total": total,
        },
        "msg": "success",
    })


def approval_record_list(request):
    """审批记录：按动作逐条展示完整的审批链路。

    每条审批申请会展开为「提交审批」「审核人同意/拒绝」「业务执行结果」
    多条记录，支持按操作类型、操作人、关键词、操作时间区间筛选。
    """
    from core.pagination import parse_page_params

    from apps.system.approval.models import ApprovalRequest
    from apps.system.approval.services import STATUS_NAMES, build_request_events

    page_num, page_size = parse_page_params(request)

    event_type = request.GET.get("eventType", "").strip()
    user_name = request.GET.get("userName", "").strip()
    keyword = request.GET.get("keyword", "").strip()
    status = request.GET.get("status", "").strip()
    start_time = _parse_date(request.GET.get("startTime", "").strip())
    end_time = _parse_date(request.GET.get("endTime", "").strip())

    queryset = ApprovalRequest.objects.prefetch_related("approvers").all()
    if status.isdigit():
        queryset = queryset.filter(status=int(status))
    if keyword:
        queryset = queryset.filter(
            Q(name__icontains=keyword)
            | Q(target_name__icontains=keyword)
            | Q(summary__icontains=keyword)
        )

    records = []
    for approval_request in queryset.order_by("-created_at", "-id"):
        for event in build_request_events(approval_request):
            records.append({
                "requestId": approval_request.id,
                "type": event["type"],
                "typeName": event["type_name"],
                "actor": event["actor"],
                "name": approval_request.name,
                "targetName": approval_request.target_name or "",
                "summary": approval_request.summary or "",
                "detail": event["detail"],
                "time": event["time"],
                "status": approval_request.status,
                "statusName": STATUS_NAMES.get(approval_request.status, "待审批"),
                "executeError": approval_request.execute_error or "",
            })

    if event_type:
        records = [item for item in records if item["type"] == event_type]
    if user_name:
        records = [item for item in records if user_name in item["actor"]]
    if start_time:
        records = [item for item in records if item["time"] and item["time"][:10] >= start_time.isoformat()]
    if end_time:
        records = [item for item in records if item["time"] and item["time"][:10] <= end_time.isoformat()]

    records.sort(key=lambda item: (item["time"], item["requestId"]), reverse=True)
    total = len(records)
    start_idx = (page_num - 1) * page_size
    page_records = records[start_idx:start_idx + page_size]

    return JsonResponse({
        "code": "00000",
        "data": {
            "list": page_records,
            "total": total,
        },
        "msg": "success",
    })


def _parse_date(value):
    """解析 YYYY-MM-DD 日期，非法值返回 None（忽略该筛选条件）。"""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
