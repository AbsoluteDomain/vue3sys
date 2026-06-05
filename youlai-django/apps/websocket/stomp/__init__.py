"""
STOMP over WebSocket 模块

提供 STOMP 协议的 WebSocket 实现，与前端 @stomp/stompjs 客户端兼容。
"""

from .frame import (
    Frame,
    Command,
    Header,
    unmarshal,
    new_connected_frame,
    new_message_frame,
    new_error_frame,
    new_receipt_frame,
)

from .consumer import (
    StompConsumer,
    StompBroker,
    StompConnection,
    broker,
    broadcast_to_topic,
    send_to_user,
    get_online_user_count,
)

__all__ = [
    # Frame
    "Frame",
    "Command",
    "Header",
    "unmarshal",
    "new_connected_frame",
    "new_message_frame",
    "new_error_frame",
    "new_receipt_frame",
    # Consumer
    "StompConsumer",
    "StompBroker",
    "StompConnection",
    "broker",
    "broadcast_to_topic",
    "send_to_user",
    "get_online_user_count",
]
