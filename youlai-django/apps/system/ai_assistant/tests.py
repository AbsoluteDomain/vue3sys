"""系统管理-AI 助手单元测试。

覆盖：参数校验、未配置 API Key、流式内容转发。
"""
import json
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings

from . import views


class AiChatTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def post(self, payload):
        return self.factory.post(
            "/api/v1/ai/chat",
            data=json.dumps(payload),
            content_type="application/json",
        )

    @override_settings(DEEPSEEK_API_KEY="")
    def test_missing_api_key(self):
        response = views.chat(self.post({"messages": [{"role": "user", "content": "你好"}]}))

        self.assertEqual(response.status_code, 400)
        self.assertIn("DEEPSEEK_API_KEY", json.loads(response.content)["msg"])

    def test_empty_messages(self):
        response = views.chat(self.post({}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["code"], "A0400")

    def test_last_message_must_be_user(self):
        response = views.chat(
            self.post({"messages": [{"role": "assistant", "content": "你好"}]})
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("请先输入要发送的消息", json.loads(response.content)["msg"])

    @override_settings(DEEPSEEK_API_KEY="test-key")
    def test_stream_relays_deltas(self):
        upstream = MagicMock()
        upstream.status_code = 200
        upstream.iter_lines.return_value = iter(
            [
                b'data: {"choices": [{"delta": {"content": "\xe4\xbd\xa0"}}]}',
                b"",
                b'data: {"choices": [{"delta": {"content": "\xe5\xa5\xbd"}}]}',
                b"data: [DONE]",
            ]
        )

        with patch(
            "apps.system.ai_assistant.views.requests.post", return_value=upstream
        ) as post:
            response = views.chat(self.post({"messages": [{"role": "user", "content": "hi"}]}))
            body = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("text/event-stream", response["Content-Type"])
        self.assertIn("你", body)
        self.assertIn("好", body)
        self.assertIn('"done": true', body)
        self.assertTrue(post.call_args.kwargs["json"]["stream"])
        upstream.close.assert_called()

    @override_settings(DEEPSEEK_API_KEY="test-key")
    def test_upstream_error_returns_502(self):
        upstream = MagicMock()
        upstream.status_code = 500
        upstream.text = "server error"

        with patch("apps.system.ai_assistant.views.requests.post", return_value=upstream):
            response = views.chat(self.post({"messages": [{"role": "user", "content": "hi"}]}))

        self.assertEqual(response.status_code, 502)
        self.assertIn("AI 服务返回异常", json.loads(response.content)["msg"])
