"""数据权限模块。

支持多角色数据权限合并（并集策略）：
- 如果任一角色是 ALL，则跳过数据权限过滤
- 否则用 OR 连接各角色的数据权限条件
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Callable
from functools import wraps

from django.db.models import Q, QuerySet

from apps.system.roles.models import Role, RoleDept
from apps.system.users.models import User, UserRole
from apps.system.dept.models import Department


# 数据权限枚举
class DataScopeEnum:
    """数据权限范围枚举"""
    ALL = 1           # 全部数据
    DEPT_AND_SUB = 2  # 本部门及子部门
    DEPT = 3          # 本部门
    SELF = 4          # 仅本人
    CUSTOM = 5        # 自定义部门


@dataclass
class RoleDataScope:
    """角色数据权限"""
    role_code: str
    data_scope: int
    custom_dept_ids: Optional[List[int]] = None

    @classmethod
    def from_role(cls, role: Role) -> 'RoleDataScope':
        """从角色创建数据权限对象"""
        custom_dept_ids = None
        if role.data_scope == DataScopeEnum.CUSTOM:
            custom_dept_ids = list(
                RoleDept.objects.filter(role_id=role.id).values_list('dept_id', flat=True)
            )
        return cls(
            role_code=role.code,
            data_scope=role.data_scope or DataScopeEnum.SELF,
            custom_dept_ids=custom_dept_ids
        )


def get_user_data_scopes(user: User) -> List[RoleDataScope]:
    """获取用户所有角色的数据权限列表"""
    if user.is_superuser:
        return [RoleDataScope(role_code='SUPER', data_scope=DataScopeEnum.ALL)]

    role_ids = UserRole.objects.filter(user_id=user.id).values_list('role_id', flat=True)
    if not role_ids:
        return []

    roles = Role.objects.filter(id__in=role_ids)
    return [RoleDataScope.from_role(role) for role in roles]


def has_all_data_scope(data_scopes: List[RoleDataScope]) -> bool:
    """判断是否有全部数据权限"""
    return any(ds.data_scope == DataScopeEnum.ALL for ds in data_scopes)


def get_dept_and_sub_ids(dept_id: int) -> List[int]:
    """获取部门及其所有子部门ID"""
    if not dept_id:
        return []

    result = [dept_id]
    children = Department.objects.filter(parent_id=dept_id, is_deleted=0)
    for child in children:
        result.extend(get_dept_and_sub_ids(child.id))
    return result


class DataPermissionHandler:
    """数据权限处理器"""

    @staticmethod
    def build_q_expression(
        data_scopes: List[RoleDataScope],
        dept_field: str = 'dept_id',
        user_field: str = 'id',
        current_user_id: Optional[int] = None,
        current_dept_id: Optional[int] = None
    ) -> Q:
        """构建多角色并集查询条件"""
        if not data_scopes:
            return Q(pk__in=[])  # 无权限

        # 任一角色有全部数据权限
        if has_all_data_scope(data_scopes):
            return Q()

        expressions = []
        for ds in data_scopes:
            expr = DataPermissionHandler._build_role_expression(
                ds, dept_field, user_field, current_user_id, current_dept_id
            )
            if expr is not None:
                expressions.append(expr)

        if not expressions:
            return Q(pk__in=[])  # 无权限

        # OR 连接各角色条件
        result = expressions[0]
        for expr in expressions[1:]:
            result |= expr
        return result

    @staticmethod
    def _build_role_expression(
        data_scope: RoleDataScope,
        dept_field: str,
        user_field: str,
        current_user_id: Optional[int],
        current_dept_id: Optional[int]
    ) -> Optional[Q]:
        """构建单角色数据权限条件"""
        if data_scope.data_scope == DataScopeEnum.ALL:
            return None

        if data_scope.data_scope == DataScopeEnum.DEPT_AND_SUB:
            if current_dept_id:
                dept_ids = get_dept_and_sub_ids(current_dept_id)
                return Q(**{f'{dept_field}__in': dept_ids})
            return Q(pk__in=[])

        if data_scope.data_scope == DataScopeEnum.DEPT:
            if current_dept_id:
                return Q(**{dept_field: current_dept_id})
            return Q(pk__in=[])

        if data_scope.data_scope == DataScopeEnum.SELF:
            if current_user_id:
                return Q(**{user_field: current_user_id})
            return Q(pk__in=[])

        if data_scope.data_scope == DataScopeEnum.CUSTOM:
            if data_scope.custom_dept_ids:
                return Q(**{f'{dept_field}__in': data_scope.custom_dept_ids})
            return Q(pk__in=[])

        return None


def apply_data_permission(
    queryset: QuerySet,
    user: User,
    dept_field: str = 'dept_id',
    user_field: str = 'id'
) -> QuerySet:
    """应用数据权限过滤"""
    if user.is_superuser:
        return queryset

    data_scopes = get_user_data_scopes(user)
    if has_all_data_scope(data_scopes):
        return queryset

    q = DataPermissionHandler.build_q_expression(
        data_scopes,
        dept_field=dept_field,
        user_field=user_field,
        current_user_id=user.id,
        current_dept_id=getattr(user, 'dept_id', None)
    )

    return queryset.filter(q)


class DataPermission:
    """数据权限装饰器

    用法：
        @DataPermission(dept_field='dept_id', user_field='create_by')
        def list(self, request, *args, **kwargs):
            queryset = self.get_queryset()
            # queryset 会自动应用数据权限过滤
    """

    def __init__(
        self,
        dept_field: str = 'dept_id',
        user_field: str = 'create_by'
    ):
        self.dept_field = dept_field
        self.user_field = user_field

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            # 在视图中注入数据权限配置
            request._data_permission_config = {
                'dept_field': self.dept_field,
                'user_field': self.user_field
            }
            return func(view, request, *args, **kwargs)
        return wrapper


class SkipDataPermission:
    """跳过数据权限装饰器"""

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(view, request, *args, **kwargs):
            request._skip_data_permission = True
            return func(view, request, *args, **kwargs)
        return wrapper


def get_viewable_user_ids(user: User) -> Any:
    """获取用户可查看的用户ID范围。

    返回 "all" 或用户ID列表
    """
    if user.is_superuser:
        return "all"

    data_scopes = get_user_data_scopes(user)
    if has_all_data_scope(data_scopes):
        return "all"

    if not data_scopes:
        return [user.id]

    user_ids = set()
    for ds in data_scopes:
        if ds.data_scope == DataScopeEnum.ALL:
            return "all"

        if ds.data_scope == DataScopeEnum.DEPT_AND_SUB:
            if user.dept_id:
                dept_ids = get_dept_and_sub_ids(user.dept_id)
                ids = User.objects.filter(
                    dept_id__in=dept_ids, is_deleted=0, status=1
                ).values_list('id', flat=True)
                user_ids.update(ids)

        elif ds.data_scope == DataScopeEnum.DEPT:
            if user.dept_id:
                ids = User.objects.filter(
                    dept_id=user.dept_id, is_deleted=0, status=1
                ).values_list('id', flat=True)
                user_ids.update(ids)

        elif ds.data_scope == DataScopeEnum.SELF:
            ids = User.objects.filter(
                create_by=user.id, is_deleted=0, status=1
            ).values_list('id', flat=True)
            user_ids.update(ids)

        elif ds.data_scope == DataScopeEnum.CUSTOM:
            if ds.custom_dept_ids:
                ids = User.objects.filter(
                    dept_id__in=ds.custom_dept_ids, is_deleted=0, status=1
                ).values_list('id', flat=True)
                user_ids.update(ids)

    if not user_ids:
        return [user.id]

    return list(user_ids)


def has_permission_to_user(current_user: User, target_user_id: int) -> bool:
    """判断当前用户是否有权限操作目标用户"""
    if current_user.is_superuser:
        return True

    if current_user.id == target_user_id:
        return True

    data_scopes = get_user_data_scopes(current_user)
    if has_all_data_scope(data_scopes):
        return True

    if not data_scopes:
        return False

    try:
        target_user = User.objects.get(id=target_user_id)
    except User.DoesNotExist:
        return False

    for ds in data_scopes:
        if ds.data_scope == DataScopeEnum.ALL:
            return True

        if ds.data_scope == DataScopeEnum.DEPT_AND_SUB:
            if current_user.dept_id:
                dept_ids = get_dept_and_sub_ids(current_user.dept_id)
                if target_user.dept_id in dept_ids:
                    return True

        elif ds.data_scope == DataScopeEnum.DEPT:
            if current_user.dept_id and target_user.dept_id == current_user.dept_id:
                return True

        elif ds.data_scope == DataScopeEnum.SELF:
            if getattr(target_user, 'create_by', None) == current_user.id:
                return True

        elif ds.data_scope == DataScopeEnum.CUSTOM:
            if ds.custom_dept_ids and target_user.dept_id in ds.custom_dept_ids:
                return True

    return False


def data_permission_required(user_or_token, operation: str = None, target_user_id: int = None):
    """数据权限校验入口。

    Args:
        user_or_token: User 对象或 JWT token 字符串
        operation: 操作类型 "select" / "add" / "update" / "delete"
        target_user_id: 目标用户ID（add/update/delete 时需要）

    Returns:
        select: 返回 "all" 或可查看的用户ID列表
        add/update/delete: 返回 bool
    """
    from rest_framework.exceptions import ValidationError

    user = user_or_token
    if isinstance(user_or_token, str) and user_or_token:
        from rest_framework_simplejwt.backends import TokenBackend
        token_backend = TokenBackend(algorithm="HS256")
        try:
            token_data = token_backend.decode(user_or_token.split(" ")[-1], verify=False)
            user_id = token_data.get("user_id")
            if not user_id:
                raise ValidationError({"code": "A0301", "msg": "无效的用户ID"})
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValidationError({"code": "A0201", "msg": "用户不存在"})
        except Exception as e:
            raise ValidationError({"code": "A0230", "msg": f"令牌解析失败: {e}"})

    if user is None:
        return [] if operation == "select" else False

    if getattr(user, "is_deleted", 0) == 1:
        raise ValidationError({"code": "A0301", "msg": "用户已删除"})

    if getattr(user, "status", 1) == 0:
        raise ValidationError({"code": "A0301", "msg": "用户已禁用"})

    if operation == "select":
        return get_viewable_user_ids(user)
    elif operation in ("add", "update", "delete"):
        if target_user_id is None:
            raise ValidationError({"code": "A0402", "msg": "未提供目标用户ID"})
        return has_permission_to_user(user, target_user_id)

    raise ValidationError({"code": "A0402", "msg": f"不支持的操作: {operation}"})
