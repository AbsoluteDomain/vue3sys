from django.http import JsonResponse
from django.db.models import Q

from core.datetime import format_local_datetime
from .models import OperationLog
from .services import MODULE_DISPLAY_NAMES


def get_module_name(module):
    """获取模块显示名称"""
    return MODULE_DISPLAY_NAMES.get(module, module)


def operation_log_list(request):
    try:
        page_num = int(request.GET.get("pageNum", 1))
    except (TypeError, ValueError):
        page_num = 1
    try:
        page_size = int(request.GET.get("pageSize", 10))
    except (TypeError, ValueError):
        page_size = 10
    
    if page_num < 1:
        page_num = 1
    if page_size < 1:
        page_size = 10
    
    module = request.GET.get("module", "").strip()
    operation_type = request.GET.get("operationType", "").strip()
    user_name = request.GET.get("userName", "").strip()
    
    logs = OperationLog.objects.all().order_by("-create_time")
    
    if module == "bom":
        logs = logs.filter(module__in=["bom", "productBom"])
    elif module == "product":
        logs = logs.filter(module__in=["product", "productStock"])
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
