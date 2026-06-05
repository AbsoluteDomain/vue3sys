"""系统管理-utils模块。

"""

import random
import string
import logging
from django.conf import settings
from django.core.mail import send_mail
from django_redis import get_redis_connection


_logger = logging.getLogger(__name__)


def _mask_email(email):
    if not email:
        return email
    e = str(email)
    if "@" not in e:
        return "***"
    name, domain = e.split("@", 1)
    name_masked = (name[:2] + "***") if len(name) >= 2 else "***"
    return f"{name_masked}@{domain}"


def generate_email_code():
    """
    生成邮箱验证码
    
    根据settings.py中的配置生成指定类型和长度的验证码
    """
    code_type = getattr(settings, 'EMAIL_CODE_TYPE', 'num')
    code_num = getattr(settings, 'EMAIL_CODE_NUM', 6)

    if code_type == 'num':
        # 纯数字验证码
        code = ''.join(random.choices(string.digits, k=code_num))
    elif code_type == 'letter':
        # 纯字母验证码
        code = ''.join(random.choices(string.ascii_letters, k=code_num))
    else:
        # 数字和字母混合验证码
        code = ''.join(random.choices(string.ascii_letters + string.digits, k=code_num))

    return code


def send_email_code(email, subject, message):
    """
    发送邮箱验证码
    
    Args:
        email: 接收验证码的邮箱地址
        subject: 邮件主题
        message: 邮件内容
    
    Returns:
        dict: 包含发送结果的字典
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return {
            "success": True,
            "message": "邮件发送成功"
        }
    except Exception as e:
        error_msg = f"发送邮件失败: {str(e)}"
        _logger.exception("send_email_code failed email=%s", _mask_email(email))
        return {
            "success": False,
            "message": error_msg
        }


def save_email_code_to_redis(email, code, user_id=None, timeout=None):
    """
    将邮箱验证码保存到Redis
    
    :param email: 邮箱地址
    :param code: 验证码
    :param user_id: 用户ID（如果提供，则将验证码与用户ID绑定）
    :param timeout: 过期时间（秒），如果不指定则使用默认超时时间
    :return: 是否保存成功
    """
    try:
        if timeout is None:
            timeout = getattr(settings, 'EMAIL_CODE_TIMEOUT', 300)

        redis_conn = get_redis_connection("default")
        redis_key = f"email_code:{email}"

        # 如果提供了用户ID，将验证码和用户ID一起存储
        if user_id:
            value = f"{code}:{user_id}"
        else:
            value = code

        redis_conn.setex(redis_key, timeout, value)
        return True
    except Exception as e:
        _logger.exception("save_email_code_to_redis failed email=%s", _mask_email(email))
        return False


def verify_email_code(email, code, user_id=None):
    """
    验证邮箱验证码
    
    :param email: 邮箱地址
    :param code: 验证码
    :param user_id: 用户ID（如果提供，则检查验证码是否与该用户ID绑定）
    :return: 验证是否通过
    """
    try:
        redis_conn = get_redis_connection("default")
        redis_key = f"email_code:{email}"
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
        _logger.exception("verify_email_code failed email=%s", _mask_email(email))
        return False


def generate_and_send_email_code(email, subject, user_id=None):
    """
    生成并发送邮箱验证码
    
    :param email: 目标邮箱
    :param subject: 邮件主题
    :param user_id: 用户ID（如果提供，则将验证码与用户ID绑定）
    :return: 发送结果
    """
    # 生成验证码
    code = generate_email_code()
    
    # 构建邮件内容
    email_code_timeout = getattr(settings, 'EMAIL_CODE_TIMEOUT', 300)
    minutes = email_code_timeout // 60
    message = f"您的验证码是: {code}，有效期为{minutes}分钟，请勿泄露给他人。"
    
    # 发送邮件
    result = send_email_code(email, subject, message)
    
    if result["success"]:
        # 存储验证码到Redis
        save_email_code_to_redis(email, code, user_id)
    
    return result
