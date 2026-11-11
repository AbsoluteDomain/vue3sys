"""系统管理-AI 助手视图。

代理调用 DeepSeek 开放对话接口（OpenAI 兼容协议），API Key 只保存在服务端，
避免在前端暴露。响应采用 SSE 流式返回，前端可逐字渲染。
"""
import json
import logging

import requests
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

# 最多携带的历史消息条数，避免上下文无限增长
MAX_MESSAGES = 20
# 单条消息最大字符数
MAX_CONTENT_LENGTH = 4000
SYSTEM_PROMPT = (
    "你是谐波减速机产品管理系统的智能助手，负责解答系统使用、产品、BOM、库存、"
    "生产计划、返修、审批流程等相关问题。回答要简洁、准确，使用中文。"
)


def _ok(data=None, msg="成功"):
    return JsonResponse({"code": "00000", "msg": msg, "data": data})


def _error(msg, code="A0400", status=400):
    return JsonResponse({"code": code, "msg": msg, "data": None}, status=status)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _parse_messages(body):
    """清洗前端传入的对话历史，返回 (错误消息, 消息列表)。"""
    raw_messages = body.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        return "消息内容不能为空", None

    messages = []
    for item in raw_messages[-MAX_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        messages.append({"role": role, "content": content[:MAX_CONTENT_LENGTH]})

    if not messages or messages[-1]["role"] != "user":
        return "请先输入要发送的消息", None
    return None, messages


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """流式对话接口：逐段返回模型回复内容。"""
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _error("请求参数格式不正确")

    error_msg, messages = _parse_messages(body)
    if error_msg:
        return _error(error_msg)

    if not settings.DEEPSEEK_API_KEY:
        return _error("未配置 DeepSeek API Key（DEEPSEEK_API_KEY），请联系管理员")

    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": True,
    }
    url = f"{settings.DEEPSEEK_API_BASE.rstrip('/')}/chat/completions"
    try:
        upstream = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.DEEPSEEK_TIMEOUT,
            stream=True,
        )
    except requests.RequestException as exc:
        logger.warning("DeepSeek 请求失败: %s", exc)
        return _error("AI 服务连接失败，请稍后重试", status=502)

    if upstream.status_code != 200:
        logger.warning(
            "DeepSeek 返回异常 status=%s body=%s", upstream.status_code, upstream.text[:500]
        )
        upstream.close()
        return _error(f"AI 服务返回异常（{upstream.status_code}）", status=502)

    def event_stream():
        try:
            for raw_line in upstream.iter_lines():
                if not raw_line:
                    continue
                if not raw_line.startswith(b"data:"):
                    continue
                data = raw_line[5:].strip()
                if data == b"[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content") or ""
                except (ValueError, KeyError, IndexError, TypeError):
                    continue
                if delta:
                    yield _sse({"content": delta})
        except requests.RequestException as exc:
            logger.warning("DeepSeek 流式读取中断: %s", exc)
            yield _sse({"error": "AI 服务连接中断，请稍后重试"})
        finally:
            upstream.close()
        yield _sse({"done": True})

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    # 关闭 nginx 缓冲，保证逐字输出
    response["X-Accel-Buffering"] = "no"
    return response
