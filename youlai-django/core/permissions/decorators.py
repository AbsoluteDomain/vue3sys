"""decorators 模块。

"""

from functools import wraps


"""权限装饰器。

在视图方法入口处做权限校验：
- 未认证直接拒绝
- 已认证但无权限直接拒绝
"""


def permission_required(perms):
    """声明当前视图需要具备的权限集合。"""
    def decorator(func):
        setattr(func, "required_perms", perms)
        return wraps(func)(func)

    return decorator
