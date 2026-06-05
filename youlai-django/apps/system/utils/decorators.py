"""系统管理-utils模块。

"""

import time
from functools import wraps

import jwt
from django.utils.timezone import now
from rest_framework_simplejwt.backends import TokenBackend  # 使用 simplejwt 的 TokenBackend
from user_agents import parse  # 引入 user-agents 库用于解析浏览器信息

from apps.system.logs.models import Log
from apps.system.users.models import User  # 从自定义的 User 模型中获取
from apps.system.utils.utils import get_ip_location


def log_api(content, module):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # 记录请求开始时间
            start_time = time.time()

            # 获取用户 ID
            user_id = None
            if request.headers.get("Authorization"):
                auth_header = request.headers.get("Authorization")
                token = auth_header.split()[1]  # 获取 Bearer token

                # 使用 simplejwt 的 TokenBackend 来解码 token
                token_backend = TokenBackend(algorithm="HS256")  # 你可以根据实际使用的算法调整
                try:
                    # 这里我们通过解码 token 获取 token 中的 payload 部分
                    token_data = token_backend.decode(token, verify=False)  # `verify=False` 如果不验证签名
                    user_id = token_data.get("user_id")  # 假设你存储了 `user_id` 在 token 中
                except jwt.DecodeError:
                    pass  # 如果 token 无效或解码失败，我们忽略该错误

            # 调用原视图函数
            response = view_func(self, request, *args, **kwargs)

            # 记录日志
            execution_time = int((time.time() - start_time) * 1000)  # 毫秒
            ip = request.META.get("REMOTE_ADDR")
            location = get_ip_location(ip)

            # 处理 location 的拆分，确保正确访问省份和城市
            if location != "本地":
                location_parts = location.split()
                province = location_parts[0] if len(location_parts) > 0 else "未知"
                city = location_parts[1] if len(location_parts) > 1 else "未知"
            else:
                province = "本地"
                city = "本地"

            # 从 User-Agent 中获取浏览器信息和操作系统
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            parsed_agent = parse(user_agent)

            browser = parsed_agent.browser.family if parsed_agent.browser.family else "未知"
            browser_version = parsed_agent.browser.version_string if parsed_agent.browser.version_string else "未知"
            os = parsed_agent.os.family if parsed_agent.os.family else "未知"

            # 获取用户昵称
            # nickname = None
            if user_id:
                try:
                    User.objects.get(id=user_id).nickname  # 从自定义的 User 模型获取昵称
                except User.DoesNotExist:
                    pass  # 如果找不到用户，保持 nickname 为 None

            # 保存日志，不依赖于响应状态码
            Log.objects.create(
                module=module,
                request_method=request.method,
                request_params=str(request.GET) + str(request.POST),
                response_content=str(response.data),  # 假设 response 是 DRF Response 对象
                content=content,
                request_uri=request.get_full_path(),
                method=view_func.__name__,
                ip=ip,
                province=province,
                city=city,
                execution_time=execution_time,
                create_by=user_id,
                create_time=now(),
                browser=browser,
                browser_version=browser_version,
                os=os
            )
            return response

        return wrapper

    return decorator
