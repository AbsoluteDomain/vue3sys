"""
STOMP over WebSocket Consumer

实现 STOMP 协议的 Django Channels Consumer
"""

import asyncio
import time
from typing import Dict, Optional, Set
from urllib.parse import parse_qs

import jwt
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.conf import settings

from .frame import (
    Frame, Command, Header,
    unmarshal, new_connected_frame, new_message_frame,
    new_error_frame, new_receipt_frame, NULL_CHAR
)


class StompConnection:
    """STOMP 连接信息"""

    def __init__(self, connection_id: str, user_id: int, username: str):
        self.connection_id = connection_id
        self.user_id = user_id
        self.username = username
        self.subscriptions: Dict[str, str] = {}  # subscription_id -> destination
        self.last_activity: float = time.time()


class StompBroker:
    """
    STOMP 消息代理（单例）

    管理所有连接、订阅和消息分发
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        # 连接管理
        self.connections: Dict[str, StompConnection] = {}  # connection_id -> connection
        self.user_connections: Dict[int, Set[str]] = {}  # user_id -> connection_ids
        # 订阅管理
        self.subscriptions: Dict[str, Set[str]] = {}  # destination -> connection_ids
        # 消息计数器
        self.message_counter = 0
        # 通道层
        self.channel_layer = get_channel_layer()

    def register_connection(self, connection: StompConnection):
        """注册连接"""
        self.connections[connection.connection_id] = connection

        if connection.user_id:
            if connection.user_id not in self.user_connections:
                self.user_connections[connection.user_id] = set()
            self.user_connections[connection.user_id].add(connection.connection_id)

    def unregister_connection(self, connection_id: str):
        """注销连接"""
        connection = self.connections.pop(connection_id, None)
        if not connection:
            return

        # 移除用户连接映射
        if connection.user_id and connection.user_id in self.user_connections:
            self.user_connections[connection.user_id].discard(connection_id)
            if not self.user_connections[connection.user_id]:
                del self.user_connections[connection.user_id]

        # 移除订阅
        for subscription_id, destination in connection.subscriptions.items():
            if destination in self.subscriptions:
                self.subscriptions[destination].discard(connection_id)
                if not self.subscriptions[destination]:
                    del self.subscriptions[destination]

    def subscribe(self, connection_id: str, subscription_id: str, destination: str):
        """订阅主题"""
        connection = self.connections.get(connection_id)
        if not connection:
            return

        # 记录连接的订阅
        connection.subscriptions[subscription_id] = destination

        # 添加到主题订阅列表
        if destination not in self.subscriptions:
            self.subscriptions[destination] = set()
        self.subscriptions[destination].add(connection_id)

    def unsubscribe(self, connection_id: str, subscription_id: str):
        """取消订阅"""
        connection = self.connections.get(connection_id)
        if not connection:
            return

        destination = connection.subscriptions.pop(subscription_id, None)
        if not destination:
            return

        # 从主题订阅列表中移除
        if destination in self.subscriptions:
            self.subscriptions[destination].discard(connection_id)
            if not self.subscriptions[destination]:
                del self.subscriptions[destination]

    def get_subscribers(self, destination: str) -> Set[str]:
        """获取主题的订阅者"""
        return self.subscriptions.get(destination, set())

    def get_user_connections(self, user_id: int) -> Set[str]:
        """获取用户的所有连接"""
        return self.user_connections.get(user_id, set())

    def get_online_user_count(self) -> int:
        """获取在线用户数"""
        return len(self.user_connections)

    def get_total_connection_count(self) -> int:
        """获取总连接数"""
        return len(self.connections)

    def get_next_message_id(self) -> str:
        """获取下一个消息 ID"""
        self.message_counter += 1
        return f"msg-{self.message_counter}"


# 全局 STOMP 代理实例
broker = StompBroker()


class StompConsumer(AsyncWebsocketConsumer):
    """
    STOMP over WebSocket Consumer

    处理 STOMP 协议的 WebSocket 连接
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connection: Optional[StompConnection] = None

    async def connect(self):
        """处理 WebSocket 连接"""
        # 从查询参数获取 token
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            await self.close(code=4001)
            return

        # 验证 token
        try:
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY),
                algorithms=["HS256"],
            )
        except jwt.InvalidTokenError:
            await self.close(code=4002)
            return

        user_id = payload.get("user_id")
        username = payload.get("username", "")

        if not user_id:
            await self.close(code=4003)
            return

        # 接受 WebSocket 连接
        await self.accept()

        # 创建 STOMP 连接信息
        self.connection = StompConnection(
            connection_id=self.channel_name,
            user_id=user_id,
            username=username
        )

        # 注册连接
        broker.register_connection(self.connection)

    async def disconnect(self, close_code):
        """处理 WebSocket 断开"""
        if self.connection:
            broker.unregister_connection(self.connection.connection_id)

    async def receive(self, text_data: str = None, bytes_data: bytes = None):
        """接收 WebSocket 消息"""
        if not text_data:
            return

        # 处理心跳（单个换行符）
        if text_data == "\n":
            if self.connection:
                self.connection.last_activity = time.time()
            return

        # 解析 STOMP 帧
        frame = unmarshal(text_data)
        if not frame:
            await self.send_error("Invalid STOMP frame")
            return

        # 更新活动时间
        if self.connection:
            self.connection.last_activity = time.time()

        # 处理 STOMP 命令
        await self.handle_frame(frame)

    async def handle_frame(self, frame: Frame):
        """处理 STOMP 帧"""
        handler_map = {
            Command.CONNECT: self.handle_connect,
            Command.SUBSCRIBE: self.handle_subscribe,
            Command.UNSUBSCRIBE: self.handle_unsubscribe,
            Command.SEND: self.handle_send,
            Command.DISCONNECT: self.handle_disconnect,
        }

        handler = handler_map.get(frame.command)
        if handler:
            await handler(frame)
        else:
            await self.send_error(f"Unknown command: {frame.command}")

    async def handle_connect(self, frame: Frame):
        """处理 CONNECT 命令"""
        # 发送 CONNECTED 帧
        connected = new_connected_frame()
        await self.send_frame(connected)

    async def handle_subscribe(self, frame: Frame):
        """处理 SUBSCRIBE 命令"""
        destination = frame.get_header(Header.DESTINATION)
        subscription_id = frame.get_header(Header.ID)

        if not destination or not subscription_id:
            await self.send_error("SUBSCRIBE requires 'destination' and 'id' headers")
            return

        # 添加订阅
        broker.subscribe(self.connection.connection_id, subscription_id, destination)

        # 加入通道层组
        await self.channel_layer.group_add(
            destination.replace("/", "_"),
            self.channel_name
        )

        # 发送收据
        receipt = frame.get_header(Header.RECEIPT)
        if receipt:
            await self.send_receipt(receipt)

    async def handle_unsubscribe(self, frame: Frame):
        """处理 UNSUBSCRIBE 命令"""
        subscription_id = frame.get_header(Header.ID)

        if not subscription_id:
            await self.send_error("UNSUBSCRIBE requires 'id' header")
            return

        # 获取订阅的目标
        destination = self.connection.subscriptions.get(subscription_id)

        # 移除订阅
        broker.unsubscribe(self.connection.connection_id, subscription_id)

        # 离开通道层组
        if destination:
            await self.channel_layer.group_discard(
                destination.replace("/", "_"),
                self.channel_name
            )

        # 发送收据
        receipt = frame.get_header(Header.RECEIPT)
        if receipt:
            await self.send_receipt(receipt)

    async def handle_send(self, frame: Frame):
        """处理 SEND 命令"""
        destination = frame.get_header(Header.DESTINATION)

        if not destination:
            await self.send_error("SEND requires 'destination' header")
            return

        # 通过通道层广播消息
        await self.channel_layer.group_send(
            destination.replace("/", "_"),
            {
                "type": "stomp_message",
                "destination": destination,
                "body": frame.body
            }
        )

        # 发送收据
        receipt = frame.get_header(Header.RECEIPT)
        if receipt:
            await self.send_receipt(receipt)

    async def handle_disconnect(self, frame: Frame):
        """处理 DISCONNECT 命令"""
        # 发送收据
        receipt = frame.get_header(Header.RECEIPT)
        if receipt:
            await self.send_receipt(receipt)

        # 关闭连接
        await self.close()

    async def stomp_message(self, event):
        """处理来自通道层的 STOMP 消息"""
        destination = event["destination"]
        body = event["body"]

        # 获取此连接对目标的订阅 ID
        subscription_id = None
        for sub_id, dest in self.connection.subscriptions.items():
            if dest == destination:
                subscription_id = sub_id
                break

        if not subscription_id:
            return

        # 创建 MESSAGE 帧
        message_id = broker.get_next_message_id()
        frame = new_message_frame(
            destination=destination,
            subscription_id=subscription_id,
            message_id=message_id,
            body=body
        )

        await self.send_frame(frame)

    async def send_frame(self, frame: Frame):
        """发送 STOMP 帧"""
        data = frame.marshal()
        await self.send(text_data=data)

    async def send_error(self, message: str):
        """发送 ERROR 帧"""
        frame = new_error_frame(message)
        await self.send_frame(frame)

    async def send_receipt(self, receipt_id: str):
        """发送 RECEIPT 帧"""
        frame = new_receipt_frame(receipt_id)
        await self.send_frame(frame)


# ============ 广播函数 ============

async def broadcast_to_topic(destination: str, body):
    """
    广播消息到指定主题

    用法：
        from apps.websocket.stomp import broadcast_to_topic
        await broadcast_to_topic("/topic/online-count", {"count": 10})
    """
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        destination.replace("/", "_"),
        {
            "type": "stomp_message",
            "destination": destination,
            "body": body
        }
    )


async def send_to_user(user_id: int, destination: str, body):
    """
    发送消息给指定用户

    用法：
        from apps.websocket.stomp import send_to_user
        await send_to_user(1, "/user/queue/messages", {"content": "Hello"})
    """
    # 获取用户的所有连接
    connection_ids = broker.get_user_connections(user_id)

    for conn_id in connection_ids:
        connection = broker.connections.get(conn_id)
        if not connection:
            continue

        # 找到订阅 ID
        subscription_id = None
        for sub_id, dest in connection.subscriptions.items():
            if dest == destination:
                subscription_id = sub_id
                break

        if not subscription_id:
            continue

        # 通过通道层发送
        await get_channel_layer().send(
            conn_id,
            {
                "type": "stomp_message",
                "destination": destination,
                "body": body
            }
        )


def get_online_user_count() -> int:
    """获取在线用户数"""
    return broker.get_online_user_count()
