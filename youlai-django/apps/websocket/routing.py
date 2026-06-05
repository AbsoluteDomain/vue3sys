"""WebSocket 路由表。

把 ws 路由和对应的 Consumer 绑定起来，类似 http 的 urls.py。

注意：Django 开发服务器（runserver）不支持 WebSocket。
请使用 ASGI 服务器运行：uvicorn config.asgi:application --reload --port 8000
"""

from django.urls import re_path

# 原生 WebSocket Consumer
from .consumers import NoticeConsumer

websocket_urlpatterns = [
    # 原生 WebSocket 端点
    # 前端需要配置：VITE_APP_WS_ENDPOINT=ws://localhost:8000/ws/notice
    re_path(r"^ws/notice$", NoticeConsumer.as_asgi()),
]

# STOMP 支持（可选，需要前端使用 @stomp/stompjs）
try:
    from .stomp.consumer import StompConsumer
    websocket_urlpatterns.insert(0, re_path(r"^ws$", StompConsumer.as_asgi()))
except ImportError:
    pass  # STOMP 模块不可用时跳过
