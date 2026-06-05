from __future__ import annotations

import fnmatch
from typing import Any

from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission

from core.permissions.role_perm_service import _normalize_perms, get_role_perms


class HasPerm(BasePermission):
    def has_permission(self, request, view) -> bool:
        action = getattr(view, "action", None)
        if not action:
            return True

        handler = getattr(view, action, None)
        required_perms = getattr(handler, "required_perms", None)
        perms = _normalize_perms(required_perms)
        if not perms:
            return True

        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            raise NotAuthenticated("未认证，请先登录")

        if getattr(user, "is_superuser", False):
            return True

        role_codes: list[str] = []
        try:
            roles_manager = getattr(user, "roles", None)
            if roles_manager is not None:
                role_codes = list(roles_manager.filter(is_deleted=False, status=1).values_list("code", flat=True))
        except Exception:
            role_codes = []

        if not role_codes:
            raise PermissionDenied("用户未分配任何角色")

        # ROOT 角色直接放行
        if "ROOT" in role_codes:
            return True

        # 从角色维度缓存获取权限
        role_perm_patterns = get_role_perms(role_codes)

        if not role_perm_patterns:
            raise PermissionDenied("权限不足，无法执行此操作")

        for required_perm in perms:
            if not any(fnmatch.fnmatchcase(required_perm, pattern) for pattern in role_perm_patterns):
                raise PermissionDenied("权限不足，无法执行此操作")

        return True
