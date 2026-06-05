import json
import logging
from .models import OperationLog

logger = logging.getLogger(__name__)


def log_operation(user_id, user_name, module, operation_type, target_id, target_name, 
                  before_data=None, after_data=None, description="", ip=None):
    """记录操作日志"""
    try:
        # 检查必填字段
        if not user_id or not user_name:
            return
        
        # 构建日志数据
        log_data = {
            "user_id": user_id,
            "user_name": user_name,
            "module": module,
            "operation_type": operation_type,
            "target_id": target_id,
            "target_name": target_name,
            "description": description,
            "ip": ip,
        }
        
        # 只在有数据时添加字段
        if before_data:
            log_data["before_data"] = json.dumps(before_data, ensure_ascii=False)
        if after_data:
            log_data["after_data"] = json.dumps(after_data, ensure_ascii=False)
        
        OperationLog.objects.create(**log_data)
    except Exception as e:
        # 记录日志失败不应该影响主业务
        logger.error(f"记录操作日志失败: {str(e)}")
