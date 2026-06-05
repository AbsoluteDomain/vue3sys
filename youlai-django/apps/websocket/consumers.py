"""WebSocket 消息处理中心。

这里定义了项目 WebSocket 的消费者 (Consumer)，专门负责处理实时的双向通信。
比如，当一个用户连接上来时，`NoticeConsumer` 会处理握手、验证身份，
然后把他加入到一个专属的通信组里。当有新消息（比如系统通知）要发给他时，
就可以通过这个组来精确推送。

"""

from urllib.parse import parse_qs

import jwt
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings


class NoticeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            await self.close()
            return

        try:
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY),
                algorithms=["HS256"],
            )
        except jwt.InvalidTokenError:
            await self.close()
            return

        user_id = payload.get("user_id")
        if not user_id:
            await self.close()
            return

        self.user_id = user_id
        self.user_group_name = f"user_{user_id}"

        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.channel_layer.group_add("notice_broadcast", self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        await self.channel_layer.group_discard("notice_broadcast", self.channel_name)

    async def receive_json(self, content, **kwargs):
        return

    async def notice_broadcast(self, event):
        data = event.get("data", {})
        await self.send_json(data)

    async def notice_personal(self, event):
        data = event.get("data", {})
        await self.send_json(data)
