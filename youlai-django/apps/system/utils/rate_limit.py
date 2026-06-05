"""系统管理-utils模块。

"""

from functools import wraps
from django.http import HttpRequest
from django_redis import get_redis_connection
from core.response import error


def ip_rate_limit(seconds: int = 60):
    """
    IP访问频率限制装饰器
    
    :param seconds: 限制时间（秒），在此时间内同一IP只能访问一次
    :return: 装饰器函数
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request: HttpRequest, *args, **kwargs):
            # 获取客户端IP
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')

            # 在Redis中检查IP是否在限制时间内
            redis_conn = get_redis_connection("default")
            redis_key = f"rate_limit:{view_func.__name__}:{ip}"

            # 如果键存在，说明在限制时间内
            if redis_conn.exists(redis_key):
                ttl = redis_conn.ttl(redis_key)
                return error(f"操作频繁，请{ttl}秒后再试", code="A0502", status=400)

            # 设置限制
            redis_conn.setex(redis_key, seconds, 1)

            # 执行原始视图函数
            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator
