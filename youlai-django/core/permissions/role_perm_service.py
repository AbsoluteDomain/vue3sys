from __future__ import annotations

import json
from typing import Any

from django.core.cache import cache
from django.db.models import Q

from apps.system.menus.models import Menu
from apps.system.roles.models import Role


# Redis Hash key: system:role:perms
# field: roleCode, value: 权限标识JSON数组
# Read-Through策略: 缓存未命中时回源DB并回写缓存
ROLE_PERMS_CACHE_KEY = "system:role:perms"


def _get_redis_client():
    """获取原生Redis客户端（用于Hash操作）"""
    from django_redis import get_redis_connection
    return get_redis_connection("default")


def _normalize_perms(perms: Any) -> list[str]:
    if perms is None:
        return []
    if isinstance(perms, str):
        return [perms]
    if isinstance(perms, (list, tuple, set)):
        return [str(p) for p in perms if p]
    return [str(perms)]


def get_role_perms_from_db(role_codes: list[str]) -> dict[str, list[str]]:
    """从数据库查询角色权限"""
    if not role_codes:
        return {}

    roles = Role.objects.filter(code__in=role_codes, is_deleted=False, status=1)
    role_ids = list(roles.values_list("id", flat=True))

    if not role_ids:
        return {code: [] for code in role_codes}

    menu_perms = (
        Menu.objects.filter(
            rolemenu__role_id__in=role_ids,
            type="B",
        )
        .exclude(Q(perm__isnull=True) | Q(perm=""))
        .values("perm", "rolemenu__role__code")
    )

    result: dict[str, list[str]] = {code: [] for code in role_codes}
    for row in menu_perms:
        role_code = row["rolemenu__role__code"]
        perm = row["perm"]
        if role_code and perm and role_code in result:
            result[role_code].append(perm)

    for code in result:
        result[code] = list(set(result[code]))

    return result


def get_role_perms(role_codes: list[str]) -> list[str]:
    """获取多个角色的权限集合（带缓存，使用 Redis Hash）"""
    if not role_codes:
        return []

    try:
        redis_client = _get_redis_client()
        perms: set[str] = set()
        missing_roles: list[str] = []

        # 批量从 Redis Hash 获取
        for role_code in role_codes:
            cached = redis_client.hget(ROLE_PERMS_CACHE_KEY, role_code)
            if cached:
                role_perms = json.loads(cached)
                perms.update(role_perms)
            else:
                missing_roles.append(role_code)

        # 回源 DB 并回写缓存
        if missing_roles:
            role_perms_map = get_role_perms_from_db(missing_roles)
            for role_code in missing_roles:
                role_perms = role_perms_map.get(role_code, [])
                perms.update(role_perms)
                # 回写到 Redis Hash
                redis_client.hset(ROLE_PERMS_CACHE_KEY, role_code, json.dumps(role_perms))

        return list(perms)
    except Exception:
        # 降级：直接查数据库
        role_perms_map = get_role_perms_from_db(role_codes)
        perms: set[str] = set()
        for role_perms in role_perms_map.values():
            perms.update(role_perms)
        return list(perms)


def refresh_role_perms_cache(role_code: str) -> None:
    """刷新单个角色的权限缓存"""
    try:
        redis_client = _get_redis_client()
        role_perms_map = get_role_perms_from_db([role_code])
        role_perms = role_perms_map.get(role_code, [])
        redis_client.hset(ROLE_PERMS_CACHE_KEY, role_code, json.dumps(role_perms))
    except Exception:
        pass


def refresh_role_perms_cache_batch(role_codes: list[str]) -> None:
    """批量刷新角色权限缓存"""
    if not role_codes:
        return

    try:
        redis_client = _get_redis_client()
        role_perms_map = get_role_perms_from_db(role_codes)
        for role_code in role_codes:
            role_perms = role_perms_map.get(role_code, [])
            redis_client.hset(ROLE_PERMS_CACHE_KEY, role_code, json.dumps(role_perms))
    except Exception:
        pass
