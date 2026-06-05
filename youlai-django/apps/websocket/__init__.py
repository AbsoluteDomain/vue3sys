"""WebSocket 模块。

提供 WebSocket 连接管理，包括原生 WebSocket 和 STOMP 协议支持。
"""

from apps.websocket.consumers import NoticeConsumer

__all__ = [
    "NoticeConsumer",
]
