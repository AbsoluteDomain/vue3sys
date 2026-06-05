"""系统管理-utils模块。

"""

import random
import string
import time
import logging
from typing import Dict, Any
from django.conf import settings
from django_redis import get_redis_connection

from alibabacloud_dysmsapi20170525.client import Client as Dysmsapi20170525Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dysmsapi20170525 import models as dysmsapi_20170525_models
from alibabacloud_tea_util import models as util_models

_logger = logging.getLogger(__name__)

def _mask_mobile(mobile: str | None) -> str | None:
    if not mobile:
        return mobile
    m = str(mobile)
    if len(m) < 7:
        return "***"
    return f"{m[:3]}****{m[-4:]}"

def generate_mobile_code(code_length: int = 6) -> str:
    """
    生成指定长度的随机数字验证码
    
    :param code_length: 验证码长度，默认6位
    :return: 生成的验证码
    """
    fixed_enabled = bool(getattr(settings, 'MOBILE_CODE_FIXED_ENABLED', False))
    if fixed_enabled:
        fixed_value = str(getattr(settings, 'MOBILE_CODE_FIXED_VALUE', '123456') or '123456')
        digits = ''.join([c for c in fixed_value if c.isdigit()])
        if not digits:
            digits = '123456'
        if code_length and code_length > 0:
            if len(digits) < code_length:
                digits = digits.zfill(code_length)
            elif len(digits) > code_length:
                digits = digits[:code_length]
        return digits
    return ''.join(random.choice('0123456789') for _ in range(code_length))

def generate_random_string(length: int) -> str:
    """
    生成指定长度的随机字母字符串
    
    :param length: 字符串长度
    :return: 生成的随机字符串
    """
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

def generate_extend_code() -> str:
    """
    生成短信上行扩展码：随机数+当前时间+随机数
    
    :return: 生成的扩展码
    """
    prefix = str(random.randint(1, 9))
    current_time = str(int(time.time()))
    suffix = str(random.randint(1, 9))
    return f"{prefix}{current_time}{suffix}"

def save_mobile_code_to_redis(mobile: str, code: str, user_id=None, timeout: int = None) -> bool:
    """
    将手机验证码保存到Redis
    
    :param mobile: 手机号
    :param code: 验证码
    :param user_id: 用户ID（如果提供，则将验证码与用户ID绑定）
    :param timeout: 过期时间（秒），默认使用配置中的过期时间
    :return: 是否保存成功
    """
    if timeout is None:
        timeout = getattr(settings, 'MOBILE_CODE_TIMEOUT', 300)

    try:
        redis_conn = get_redis_connection("default")
        redis_key = f"mobile_code:{mobile}"

        # 如果提供了用户ID，将验证码和用户ID一起存储
        if user_id:
            value = f"{code}:{user_id}"
        else:
            value = code

        redis_conn.setex(redis_key, timeout, value)
        return True
    except Exception as e:
        _logger.exception("save_mobile_code_to_redis failed mobile=%s", _mask_mobile(mobile))
        return False

def verify_mobile_code(mobile: str, code: str, user_id=None) -> bool:
    """
    验证手机验证码
    
    :param mobile: 手机号
    :param code: 验证码
    :param user_id: 用户ID（如果提供，则检查验证码是否与该用户ID绑定）
    :return: 验证是否通过
    """
    try:
        redis_conn = get_redis_connection("default")
        redis_key = f"mobile_code:{mobile}"
        stored_value = redis_conn.get(redis_key)

        if not stored_value:
            return False

        stored_value = stored_value.decode("utf-8")

        # 检查存储值是否包含用户ID
        if ":" not in stored_value:
            return False
        stored_code, stored_user_id = stored_value.split(":", 1)
        # 如果提供了用户ID，但与存储的用户ID不匹配
        if user_id and int(stored_user_id) != int(user_id):
            return False
        # 检查验证码
        if stored_code == code:
            redis_conn.delete(redis_key)
            return True

        return False
    except Exception as e:
        _logger.exception("verify_mobile_code failed mobile=%s", _mask_mobile(mobile))
        return False

def create_client() -> Dysmsapi20170525Client:
    """
    创建阿里云短信客户端
    
    :return: 短信客户端实例
    """
    config = open_api_models.Config(
        access_key_id=settings.ALIYUN_SMS_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_SMS_ACCESS_KEY_SECRET
    )
    config.endpoint = 'dysmsapi.aliyuncs.com'
    return Dysmsapi20170525Client(config)

def send_mobile_code(mobile: str, user_id=None) -> Dict[str, Any]:
    """
    发送手机验证码
    
    :param mobile: 手机号
    :param user_id: 用户ID（如果提供，则将验证码与用户ID绑定）
    :return: 发送结果
    """
    # 生成验证码
    code_length = getattr(settings, 'MOBILE_CODE_LENGTH', 6)
    code = generate_mobile_code(code_length)

    _logger.info("send_mobile_code start mobile=%s user_id=%s", _mask_mobile(mobile), user_id)

    # 验证码有效期（分钟）
    timeout_minutes = getattr(settings, 'MOBILE_CODE_TIMEOUT', 300) // 60

    # 生成随机参数
    out_id = generate_random_string(10)
    sms_up_extend_code = generate_extend_code()

    try:
        # 创建短信客户端
        client = create_client()

        # 构建短信请求
        send_sms_request = dysmsapi_20170525_models.SendSmsRequest(
            sign_name=settings.ALIYUN_SMS_SIGN_NAME,
            template_code=settings.ALIYUN_SMS_TEMPLATE_CODE,
            phone_numbers=mobile,
            template_param=f'{{"code":"{code}","time":"{timeout_minutes}"}}',
            out_id=out_id,
            sms_up_extend_code=sms_up_extend_code
        )

        # 发送短信
        runtime = util_models.RuntimeOptions()
        response = client.send_sms_with_options(send_sms_request, runtime)

        # 解析响应
        if response.body.code == "OK":
            # 发送成功，保存验证码到Redis
            save_mobile_code_to_redis(mobile, code, user_id)
            _logger.info(
                "send_mobile_code success mobile=%s request_id=%s biz_id=%s",
                _mask_mobile(mobile),
                response.body.request_id,
                response.body.biz_id,
            )
            return {
                "success": True,
                "message": "短信发送成功",
                "data": {
                    "requestId": response.body.request_id,
                    "bizId": response.body.biz_id
                }
            }
        else:
            _logger.warning(
                "send_mobile_code failed mobile=%s code=%s message=%s",
                _mask_mobile(mobile),
                response.body.code,
                response.body.message,
            )
            return {
                "success": False,
                "message": f"短信发送失败: {response.body.message}",
                "data": {
                    "requestId": response.body.request_id,
                    "code": response.body.code
                }
            }
    except Exception as e:
        _logger.exception("send_mobile_code exception mobile=%s", _mask_mobile(mobile))
        return {
            "success": False,
            "message": f"短信发送异常: {str(e)}",
            "data": None
        }
