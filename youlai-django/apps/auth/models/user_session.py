"""用户会话信息模型。

存储在Token中的用户会话快照，包含用户身份、数据权限和角色权限信息。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Set, Optional

from core.permissions.data_scope import RoleDataScope


@dataclass
class UserSession:
    """用户会话信息"""
    user_id: int
    username: str
    dept_id: Optional[int] = None
    data_scopes: List[RoleDataScope] = field(default_factory=list)
    roles: Set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        """转换为字典，用于Redis存储"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'dept_id': self.dept_id,
            'data_scopes': [
                {
                    'role_code': ds.role_code,
                    'data_scope': ds.data_scope,
                    'custom_dept_ids': ds.custom_dept_ids
                }
                for ds in self.data_scopes
            ],
            'roles': list(self.roles)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserSession':
        """从字典创建实例"""
        data_scopes = [
            RoleDataScope(
                role_code=ds['role_code'],
                data_scope=ds['data_scope'],
                custom_dept_ids=ds.get('custom_dept_ids')
            )
            for ds in data.get('data_scopes', [])
        ]
        return cls(
            user_id=data['user_id'],
            username=data['username'],
            dept_id=data.get('dept_id'),
            data_scopes=data_scopes,
            roles=set(data.get('roles', []))
        )
