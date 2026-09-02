import json
import logging
from .models import OperationLog

logger = logging.getLogger(__name__)

MODULE_DISPLAY_NAMES = {
    "product": "库存管理",
    "productStock": "库存",
    "bom": "产品BOM管理",
    "productBom": "产品BOM管理",
    "finishProduct": "成品管理",
}

DESCRIPTION_MAX_LENGTH = 500


def _request_id(request):
    return getattr(request, "request_id", "-")


def log_operation(user_id, user_name, module, operation_type, target_id, target_name,
                  before_data=None, after_data=None, description="", ip=None,
                  module_name=None):
    """记录操作日志"""
    try:
        if user_id is None or not user_name:
            return

        if description and len(description) > DESCRIPTION_MAX_LENGTH:
            description = description[: DESCRIPTION_MAX_LENGTH - 3] + "..."

        log_data = {
            "user_id": user_id,
            "user_name": user_name,
            "module": module,
            "module_name": module_name or MODULE_DISPLAY_NAMES.get(module, module),
            "operation_type": operation_type,
            "target_id": target_id,
            "target_name": target_name,
            "description": description,
            "ip": ip,
        }

        if before_data:
            log_data["before_data"] = json.dumps(before_data, ensure_ascii=False)
        if after_data:
            log_data["after_data"] = json.dumps(after_data, ensure_ascii=False)

        OperationLog.objects.create(**log_data)
    except Exception as e:
        logger.error(f"记录操作日志失败: {str(e)}")


def log_operation_from_request(request, **kwargs):
    """从 HTTP 请求解析操作用户并写入日志。"""
    from .request_user import get_client_ip, get_request_operator

    try:
        operator = get_request_operator(request)
        if not operator:
            has_auth = bool(request.META.get("HTTP_AUTHORIZATION"))
            logger.warning(
                "跳过操作日志：无法解析操作用户 request_id=%s path=%s has_auth=%s",
                _request_id(request),
                getattr(request, "path", ""),
                has_auth,
            )
            return
        user_id, user_name = operator
        kwargs.setdefault("target_id", 0)
        log_operation(
            user_id=user_id,
            user_name=user_name,
            ip=get_client_ip(request),
            **kwargs,
        )
    except Exception as e:
        logger.error(
            "记录操作日志失败 request_id=%s path=%s err=%s",
            _request_id(request),
            getattr(request, "path", ""),
            str(e),
        )
