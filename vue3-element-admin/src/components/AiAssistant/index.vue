<template>
  <div class="ai-assistant">
    <div class="ai-assistant__trigger" title="AI 助手" @click="handleOpen">
      <el-icon :size="18" class="ai-assistant__icon"><ChatDotRound /></el-icon>
    </div>

    <el-drawer
      v-model="visible"
      :size="440"
      :with-header="false"
      class="ai-assistant__drawer"
      @closed="handleClosed"
    >
      <div class="ai-chat">
        <div class="ai-chat__header">
          <span class="ai-chat__title">AI 助手</span>
          <el-button link type="primary" :disabled="loading" @click="clearMessages">
            清空对话
          </el-button>
        </div>

        <div ref="messageListRef" class="ai-chat__body">
          <div v-if="messages.length === 0" class="ai-chat__empty">
            <el-icon :size="36"><ChatDotRound /></el-icon>
            <p>你好，我是 AI 助手，有什么可以帮你？</p>
          </div>

          <div
            v-for="(item, index) in messages"
            :key="index"
            :class="['ai-chat__row', `ai-chat__row--${item.role}`]"
          >
            <div
              :class="[
                'ai-chat__bubble',
                { 'ai-chat__bubble--error': item.error },
              ]"
            >
              <template v-if="item.role === 'assistant'">
                <div
                  v-if="item.content"
                  class="md-body"
                  v-html="renderMarkdown(item.content)"
                />
                <span v-else class="ai-chat__typing">正在思考…</span>
                <span v-if="item.streaming && item.content" class="ai-chat__caret" />
              </template>
              <template v-else>{{ item.content }}</template>
            </div>

            <div v-if="item.role === 'assistant' && !item.streaming" class="ai-chat__tools">
              <el-button link size="small" @click="copyMessage(item)">复制</el-button>
              <el-button
                v-if="index === messages.length - 1"
                link
                size="small"
                @click="regenerate"
              >
                重新生成
              </el-button>
            </div>
          </div>
        </div>

        <div class="ai-chat__footer">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="3"
            resize="none"
            maxlength="1000"
            placeholder="输入消息，Enter 发送，Shift + Enter 换行"
            @keydown.enter="handleEnter"
          />
          <div class="ai-chat__actions">
            <el-button v-if="loading" @click="stopGenerating">停止生成</el-button>
            <el-button
              v-else
              type="primary"
              :disabled="!inputText.trim()"
              @click="sendMessage"
            >
              发送
            </el-button>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ChatDotRound } from "@element-plus/icons-vue";
import { streamChat } from "@/api/ai";
import { renderMarkdown } from "@/utils/markdown";

interface ChatItem {
  role: "user" | "assistant";
  content: string;
  /** 正在接收流式内容 */
  streaming?: boolean;
  /** 请求失败 */
  error?: boolean;
}

const visible = ref(false);
const loading = ref(false);
const inputText = ref("");
const messages = ref<ChatItem[]>([]);
const messageListRef = ref<HTMLElement>();
let controller: AbortController | null = null;

function handleOpen() {
  visible.value = true;
  scrollToBottom();
}

function handleClosed() {
  inputText.value = "";
}

function scrollToBottom() {
  nextTick(() => {
    const el = messageListRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

function clearMessages() {
  messages.value = [];
  inputText.value = "";
}

/** Enter 发送，Shift + Enter 换行，输入法组合中不拦截 */
function handleEnter(event: KeyboardEvent) {
  if (event.shiftKey || event.isComposing) return;
  event.preventDefault();
  sendMessage();
}

/** 组装发送给后端的对话历史，跳过失败气泡 */
function payloadMessages() {
  return messages.value
    .filter((item) => !item.error && item.content.trim())
    .map((item) => ({ role: item.role, content: item.content }));
}

async function sendMessage() {
  const text = inputText.value.trim();
  if (!text || loading.value) return;

  messages.value.push({ role: "user", content: text });
  inputText.value = "";
  await requestAnswer();
}

async function requestAnswer() {
  messages.value.push({ role: "assistant", content: "", streaming: true });
  const assistant = messages.value[messages.value.length - 1];

  loading.value = true;
  controller = new AbortController();
  scrollToBottom();

  try {
    const content = await streamChat(payloadMessages().filter((item) => !item.streaming), {
      signal: controller.signal,
      onDelta: (delta) => {
        assistant.content += delta;
        scrollToBottom();
      },
    });
    if (!assistant.content) {
      assistant.content = content || "（未返回内容）";
    }
  } catch (error: any) {
    if (error?.name === "AbortError") {
      if (!assistant.content) {
        assistant.content = "已停止生成";
      }
    } else {
      assistant.content = assistant.content || error?.message || "AI 服务暂时不可用，请稍后重试";
      assistant.error = true;
    }
  } finally {
    assistant.streaming = false;
    loading.value = false;
    controller = null;
    scrollToBottom();
  }
}

function stopGenerating() {
  controller?.abort();
}

/** 重新生成最后一条回答 */
function regenerate() {
  if (loading.value) return;
  while (messages.value.length > 0 && messages.value[messages.value.length - 1].role === "assistant") {
    messages.value.pop();
  }
  if (messages.value.length === 0) return;
  requestAnswer();
}

async function copyMessage(item: ChatItem) {
  try {
    await navigator.clipboard.writeText(item.content);
    ElMessage.success("已复制");
  } catch {
    ElMessage.error("复制失败，请手动选择内容");
  }
}
</script>

<style lang="scss" scoped>
.ai-assistant {
  display: flex;
  align-items: center;
  justify-content: center;

  &__trigger {
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  &__icon {
    color: var(--el-text-color-regular);
    transition: color 0.3s;
  }
}

.ai-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  &__title {
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  &__body {
    flex: 1;
    overflow-y: auto;
    padding: 4px 2px;
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 8px;
    color: var(--el-text-color-secondary);

    p {
      margin: 0;
      font-size: 14px;
    }
  }

  &__row {
    display: flex;
    flex-direction: column;
    margin-bottom: 12px;

    &--user {
      align-items: flex-end;
    }

    &--assistant {
      align-items: flex-start;
    }
  }

  &__bubble {
    max-width: 88%;
    padding: 10px 12px;
    font-size: 14px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
    border-radius: 8px;
    color: var(--el-text-color-primary);
    background: var(--el-fill-color-light);

    &--error {
      color: var(--el-color-danger);
    }
  }

  &__row--user &__bubble {
    color: var(--el-color-white);
    background: var(--el-color-primary);
  }

  &__typing {
    color: var(--el-text-color-secondary);
  }

  &__caret {
    display: inline-block;
    width: 6px;
    height: 14px;
    margin-left: 2px;
    vertical-align: text-bottom;
    background: var(--el-color-primary);
    animation: ai-caret-blink 1s steps(2, start) infinite;
  }

  &__tools {
    display: flex;
    gap: 4px;
    margin-top: 2px;
  }

  &__footer {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--el-border-color-lighter);
  }

  &__actions {
    display: flex;
    justify-content: flex-end;
  }
}

@keyframes ai-caret-blink {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }
}

// Markdown 渲染结果（v-html 内容需用 :deep 穿透）
.md-body {
  :deep(.md-paragraph) {
    margin: 0 0 6px;
  }

  :deep(.md-paragraph:last-child) {
    margin-bottom: 0;
  }

  :deep(.md-heading) {
    margin: 8px 0 6px;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.4;
  }

  :deep(.md-list) {
    margin: 0 0 6px;
    padding-left: 20px;
  }

  :deep(.md-code-block) {
    margin: 6px 0;
    padding: 10px;
    overflow-x: auto;
    font-family: Consolas, Monaco, "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
    background: var(--el-bg-color-page);
    border-radius: 6px;
  }

  :deep(.md-code-inline) {
    padding: 1px 4px;
    font-family: Consolas, Monaco, "Courier New", monospace;
    font-size: 12px;
    background: var(--el-bg-color-page);
    border-radius: 4px;
  }

  :deep(a) {
    color: var(--el-color-primary);
    text-decoration: none;
  }
}
</style>
