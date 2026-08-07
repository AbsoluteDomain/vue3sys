"""检查菜单分配情况"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.system.roles.models import RoleMenu
from apps.system.users.models import UserRole
from apps.system.menus.models import Menu
from django.contrib.auth import get_user_model

User = get_user_model()

# 检查各角色的菜单分配
for role_id in [1, 2, 3]:
    count = RoleMenu.objects.filter(role_id=role_id).count()
    role = Menu.objects.model
    print(f'role_id={role_id} RoleMenu count={count}')

# 检查 user_id=1 的 is_superuser
u = User.objects.get(id=1)
print(f'\nUser 1: username={u.username} is_superuser={u.is_superuser} is_staff={u.is_staff}')

# 检查 user_id=2
try:
    u2 = User.objects.get(id=2)
    print(f'User 2: username={u2.username} is_superuser={u2.is_superuser} is_staff={u2.is_staff}')
except User.DoesNotExist:
    print('User 2 does not exist')

# 检查 ADMIN 角色 (role_id=2) 的菜单分配
admin_menus = list(RoleMenu.objects.filter(role_id=2).values_list('menu_id', flat=True))
print(f'\nADMIN role (id=2) menu_ids: {admin_menus}')
print(f'ADMIN role has 2807 (产品管理): {2807 in admin_menus}')
