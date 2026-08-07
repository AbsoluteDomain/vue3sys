#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键清理/重建角色权限缓存的管理命令。

背景
----
assign_role_menus 使用 bulk_create 批量创建 RoleMenu，而 bulk_create 不触发
post_save signal，导致 Redis 中的权限缓存（system:role:perms）不会被刷新，
非 ROOT/非超管用户会因此收到 403。

用法
----
# 默认：清空缓存并立即从数据库重建（推荐，重建后立刻生效）
python manage.py clear_perm_cache

# 只删除缓存，不重建（下次有用户请求时才会回源 DB 回写）
python manage.py clear_perm_cache --delete-only

# 只查看当前缓存状态，不做任何修改
python manage.py clear_perm_cache --dry-run
"""

from django.core.management.base import BaseCommand

from apps.system.roles.models import Role
from core.permissions.role_perm_service import (
    ROLE_PERMS_CACHE_KEY,
    _get_redis_client,
    get_role_perms_from_db,
    refresh_role_perms_cache_batch,
)


class Command(BaseCommand):
    help = "一键清理/重建 Redis 中的角色权限缓存（system:role:perms）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-only",
            action="store_true",
            default=False,
            help="只删除缓存，不重建（下次请求时回源 DB）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="只查看当前缓存状态，不做任何修改",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        delete_only = options["delete_only"]

        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.MIGRATE_HEADING(" 角色权限缓存清理工具"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))

        # 1. 读取当前缓存状态
        before_state = self._get_cache_state()

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("[1/4] 当前 Redis 缓存状态："))
        if not before_state:
            self.stdout.write(self.style.WARNING("  缓存为空（Hash 不存在或无字段）"))
        else:
            self.stdout.write(f"  缓存 Key: {ROLE_PERMS_CACHE_KEY}")
            self.stdout.write(f"  角色数量: {len(before_state)}")
            self.stdout.write("  各角色权限数量：")
            for role_code, perm_count in before_state.items():
                marker = self.style.ERROR(" (空-会导致403)") if perm_count == 0 else ""
                self.stdout.write(f"    {role_code}: {perm_count} 条权限{marker}")

        # 2. dry-run 模式：只看不改
        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("[dry-run] 未做任何修改，退出。"))
            return

        # 3. 查询数据库中所有启用角色
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("[2/4] 查询数据库中的启用角色..."))
        roles = Role.objects.filter(is_deleted=False, status=1).values("code", "name")
        role_list = list(roles)
        if not role_list:
            self.stdout.write(self.style.WARNING("  数据库中无启用角色，跳过。"))
            return
        for r in role_list:
            self.stdout.write(f"    {r['code']} ({r['name']})")
        role_codes = [r["code"] for r in role_list if r["code"]]

        # 4. 删除旧缓存
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("[3/4] 删除旧缓存..."))
        try:
            redis_client = _get_redis_client()
            deleted = redis_client.delete(ROLE_PERMS_CACHE_KEY)
            self.stdout.write(self.style.SUCCESS(f"  已删除缓存 Key（影响 {deleted} 条）"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  删除缓存失败: {e}"))
            return

        if delete_only:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("[delete-only] 已删除缓存，未重建。下次请求时会回源 DB。"))
            self._print_done()
            return

        # 5. 从数据库重建缓存
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("[4/4] 从数据库重建缓存..."))
        try:
            refresh_role_perms_cache_batch(role_codes)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  重建缓存失败: {e}"))
            return

        # 6. 校验重建结果
        after_state = self._get_cache_state()
        rebuilt_count = len(after_state)
        total_perms = sum(after_state.values())
        self.stdout.write(self.style.SUCCESS(f"  重建完成：{rebuilt_count} 个角色，共 {total_perms} 条权限"))

        # 标记仍为空的角色（可能是数据库中确实没分配菜单权限）
        empty_roles = [code for code, cnt in after_state.items() if cnt == 0]
        if empty_roles:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("以下角色重建后仍无权限（请检查是否已分配菜单）："))
            for code in empty_roles:
                self.stdout.write(self.style.WARNING(f"    {code}"))

        self._print_done()

    def _get_cache_state(self) -> dict:
        """读取缓存中各角色及其权限数量。"""
        try:
            redis_client = _get_redis_client()
            all_fields = redis_client.hgetall(ROLE_PERMS_CACHE_KEY)
        except Exception:
            return {}

        result = {}
        import json
        for role_code, perms_json in all_fields.items():
            # Redis 返回 bytes，需解码
            if isinstance(role_code, bytes):
                role_code = role_code.decode("utf-8")
            if isinstance(perms_json, bytes):
                perms_json = perms_json.decode("utf-8")
            try:
                perms = json.loads(perms_json)
                result[role_code] = len(perms) if isinstance(perms, list) else 0
            except (json.JSONDecodeError, TypeError):
                result[role_code] = 0
        return result

    def _print_done(self):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
        self.stdout.write(self.style.SUCCESS(" 完成"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 60))
