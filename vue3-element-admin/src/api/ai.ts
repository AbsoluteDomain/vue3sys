import { AuthStorage } from "@/utils/auth";
import { useUserStoreHook } from "@/store/modules/user";

/** 对话消息角色 */
export interface AiChatMessage {
  role: "user" | "assistant";
  content: string;
}

/** 流式对话回调 */
export interface StreamChatOptions {
  /** 中断信号（用于「停止生成」） */
  signal?: AbortSignal;
  /** 收到增量内容时触发 */
  onDelta: (delta: string) => void;
}

const CHAT_URL = "/api/v1/ai/chat";

/**
 * 发送一次流式对话请求（axios 无法读取流，这里使用 fetch）
 *
 * @returns 完整回复内容
 */
export async function streamChat(
  messages: AiChatMessage[],
  options: StreamChatOptions
): Promise<string> {
  const response = await requestStream(messages, options.signal);

  const contentType = response.headers.get("Content-Type") || "";
  if (!response.ok || !contentType.includes("text/event-stream")) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.msg || `AI 服务请求失败（${response.status}）`);
  }
  if (!response.body) {
    throw new Error("当前浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let content = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((item) => item.startsWith("data:"));
      if (!line) continue;

      let payload: { content?: string; done?: boolean; error?: string };
      try {
        payload = JSON.parse(line.slice(5).trim());
      } catch {
        continue;
      }
      if (payload.error) {
        throw new Error(payload.error);
      }
      if (payload.content) {
        content += payload.content;
        options.onDelta(payload.content);
      }
      if (payload.done) {
        return content;
      }
    }
  }

  return content;
}

/** 发起请求，access token 失效时自动刷新并重试一次 */
async function requestStream(
  messages: AiChatMessage[],
  signal?: AbortSignal
): Promise<Response> {
  const send = () => {
    const token = AuthStorage.getAccessToken();
    return fetch(CHAT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ messages }),
      signal,
    });
  };

  let response = await send();
  if (response.status === 401) {
    try {
      await useUserStoreHook().refreshTokenOnce();
    } catch {
      throw new Error("登录已过期，请重新登录");
    }
    response = await send();
  }
  return response;
}
