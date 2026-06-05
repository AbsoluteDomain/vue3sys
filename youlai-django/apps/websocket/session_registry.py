"""WebSocket 用户会话注册表。

维护WebSocket连接的用户会话信息，支持多设备同时登录。
采用双dict结构实现高效查询：
- user_sessions_map: 用户名 -> 会话ID集合（支持多设备）
- session_details_map: 会话ID -> 会话详情（快速定位用户）
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Dict, Set, List, Optional


@dataclass
class SessionInfo:
    """WebSocket 会话详情（内部使用）。"""
    username: str
    session_id: str
    connect_time: float


@dataclass
class OnlineUserDTO:
    """在线用户信息DTO。
    
    用于返回在线用户的基本信息，包括用户名、会话数量和登录时间。
    """
    username: str
    session_count: int
    login_time: float


class UserSessionRegistry:
    """WebSocket 用户会话注册表。
    
    维护WebSocket连接的用户会话信息，支持多设备同时登录。
    采用双Map结构实现高效查询。
    """

    def __init__(self):
        # 用户会话映射表：用户名 -> 会话ID集合
        self._user_sessions_map: Dict[str, Set[str]] = {}
        # 会话详情映射表：会话ID -> 会话详情
        self._session_details_map: Dict[str, SessionInfo] = {}
        # 线程锁
        self._lock = Lock()

    def user_connected(self, username: str, session_id: str) -> None:
        """用户上线（建立WebSocket连接）。
        
        Args:
            username: 用户名
            session_id: WebSocket会话ID
        """
        with self._lock:
            if username not in self._user_sessions_map:
                self._user_sessions_map[username] = set()
            self._user_sessions_map[username].add(session_id)
            self._session_details_map[session_id] = SessionInfo(
                username=username,
                session_id=session_id,
                connect_time=time.time()
            )

    def user_disconnected(self, username: str) -> None:
        """用户下线（断开所有WebSocket连接）。
        
        移除该用户的所有会话信息。
        
        Args:
            username: 用户名
        """
        with self._lock:
            sessions = self._user_sessions_map.pop(username, None)
            if sessions:
                for session_id in sessions:
                    self._session_details_map.pop(session_id, None)

    def remove_session(self, session_id: str) -> None:
        """移除指定会话（单设备下线）。
        
        当用户某一设备断开连接时调用，保留其他设备的会话。
        
        Args:
            session_id: WebSocket会话ID
        """
        with self._lock:
            session_info = self._session_details_map.pop(session_id, None)
            if not session_info:
                return

            username = session_info.username
            sessions = self._user_sessions_map.get(username)
            if sessions:
                sessions.discard(session_id)
                if not sessions:
                    # 该用户没有任何会话了，移除用户记录
                    self._user_sessions_map.pop(username, None)

    def get_online_user_count(self) -> int:
        """获取在线用户数量。
        
        Returns:
            当前在线用户数（非会话数）
        """
        return len(self._user_sessions_map)

    def get_user_session_count(self, username: str) -> int:
        """获取指定用户的会话数量。
        
        Args:
            username: 用户名
            
        Returns:
            该用户的WebSocket会话数量（多设备登录时大于1）
        """
        sessions = self._user_sessions_map.get(username)
        return len(sessions) if sessions else 0

    def get_total_session_count(self) -> int:
        """获取在线会话总数。
        
        Returns:
            所有WebSocket会话的总数（包含多设备）
        """
        return len(self._session_details_map)

    def is_user_online(self, username: str) -> bool:
        """检查用户是否在线。
        
        Args:
            username: 用户名
            
        Returns:
            是否在线（至少有一个活跃会话）
        """
        sessions = self._user_sessions_map.get(username)
        return bool(sessions)

    def get_online_users(self) -> List[OnlineUserDTO]:
        """获取所有在线用户列表。
        
        Returns:
            在线用户信息列表
        """
        result = []
        with self._lock:
            for username, sessions in self._user_sessions_map.items():
                # 取最早的连接时间作为登录时间
                earliest_login_time = float('inf')
                for session_id in sessions:
                    session_info = self._session_details_map.get(session_id)
                    if session_info and session_info.connect_time < earliest_login_time:
                        earliest_login_time = session_info.connect_time

                if earliest_login_time == float('inf'):
                    earliest_login_time = time.time()

                result.append(OnlineUserDTO(
                    username=username,
                    session_count=len(sessions),
                    login_time=earliest_login_time
                ))
        return result


# 全局单例
_user_session_registry: Optional[UserSessionRegistry] = None


def get_user_session_registry() -> UserSessionRegistry:
    """获取全局用户会话注册表实例。"""
    global _user_session_registry
    if _user_session_registry is None:
        _user_session_registry = UserSessionRegistry()
    return _user_session_registry
