from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.system.menus.models import Menu
from apps.system.roles.models import RoleMenu
from core.permissions.role_perm_service import refresh_role_perms_cache, refresh_role_perms_cache_batch


@receiver(post_save, sender=RoleMenu)
@receiver(post_delete, sender=RoleMenu)
def _refresh_on_role_menu_change(sender, instance, **kwargs):
    """角色菜单变更时刷新该角色的权限缓存"""
    role = getattr(instance, "role", None)
    if role and role.code:
        refresh_role_perms_cache(role.code)


@receiver(post_save, sender=Menu)
@receiver(post_delete, sender=Menu)
def _refresh_on_menu_change(sender, instance, **kwargs):
    """菜单权限标识变更时刷新相关角色的权限缓存"""
    menu_id = getattr(instance, "id", None)
    if not menu_id:
        return

    role_codes = list(
        RoleMenu.objects.filter(menu_id=menu_id)
        .select_related("role")
        .values_list("role__code", flat=True)
        .distinct()
    )
    if role_codes:
        refresh_role_perms_cache_batch(role_codes)
