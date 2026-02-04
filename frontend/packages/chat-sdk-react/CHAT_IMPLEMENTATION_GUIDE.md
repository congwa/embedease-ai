# 聊天室实现指南

本文档说明如何使用 `@embedease/chat-sdk-react` 和相关组件构建一个完整的聊天室。

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                        ChatApp                              │
│  (顶层组件，管理 WebSocket 连接和整体状态)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      ChatContent                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│  │   Header        │ │  消息区域       │ │  输入区域      │ │
│  │   (标题栏)      │ │  (Timeline)     │ │  (ChatInput)  │ │
│  └─────────────────┘ └─────────────────┘ └───────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       Store 层                              │
│  useChatStore (状态管理) + chat-adapter (SDK 抽象)          │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. 状态管理：`useChatStore`

```typescript
// stores/chat-store.ts
import { useChatStore } from "@/stores";

// 获取状态
const timeline = useChatStore((s) => s.timelineState.timeline);
const isStreaming = useChatStore((s) => s.isStreaming);
const error = useChatStore((s) => s.error);

// 获取方法
const sendMessage = useChatStore((s) => s.sendMessage);
const abortStream = useChatStore((s) => s.abortStream);
const loadMessages = useChatStore((s) => s.loadMessages);
```

**核心状态：**

| 状态 | 类型 | 说明 |
|-----|------|------|
| `timelineState.timeline` | `TimelineItem[]` | 消息列表 |
| `isStreaming` | `boolean` | 是否正在流式响应 |
| `isLoading` | `boolean` | 是否正在加载历史 |
| `error` | `string \| null` | 错误信息 |
| `isHumanMode` | `boolean` | 是否人工客服模式 |

**核心方法：**

| 方法 | 说明 |
|-----|------|
| `sendMessage(content, images?)` | 发送消息，触发 AI 响应 |
| `abortStream()` | 中止当前流式响应 |
| `loadMessages(conversationId)` | 加载历史消息 |
| `clearMessages()` | 清空消息 |
| `addUserMessageOnly(content)` | 仅添加用户消息（人工模式） |

---

### 2. 消息区域：`ChatContainerRoot` + `ChatContainerContent`

使用 `use-stick-to-bottom` 库实现自动滚动到底部。

```tsx
import {
  ChatContainerRoot,
  ChatContainerContent,
} from "@/components/prompt-kit/chat-container";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";

function MessageArea({ timeline }: { timeline: TimelineItem[] }) {
  return (
    <div className="relative flex-1 overflow-y-auto">
      {/* ChatContainerRoot 封装了 StickToBottom */}
      <ChatContainerRoot className="h-full">
        <ChatContainerContent className="space-y-3 px-5 py-12">
          {/* 空状态 */}
          {timeline.length === 0 && <EmptyState />}

          {/* 渲染消息列表 */}
          {timeline.map((item) => renderTimelineItem(item))}
        </ChatContainerContent>

        {/* 滚动到底部按钮 */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
          <ScrollButton className="shadow-sm" />
        </div>
      </ChatContainerRoot>
    </div>
  );
}
```

**自动滚动原理：**

1. `ChatContainerRoot` 内部使用 `StickToBottom` 组件
2. 当内容变化时，自动滚动到底部（如果已在底部）
3. 用户向上滚动时，不会强制滚动
4. `ScrollButton` 通过 `useStickToBottomContext` 获取滚动状态和方法

```tsx
// components/prompt-kit/scroll-button.tsx
import { useStickToBottomContext } from "use-stick-to-bottom";

function ScrollButton() {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();

  return (
    <Button
      className={!isAtBottom ? "opacity-100" : "opacity-0"}
      onClick={() => scrollToBottom()}
    >
      <ChevronDown />
    </Button>
  );
}
```

---

### 3. 消息渲染：Timeline Item 组件

根据 `item.type` 渲染不同组件：

```tsx
import {
  LLMCallCluster,
  TimelineUserMessageItem,
  TimelineErrorItem,
  TimelineToolCallItem,
  TimelineSupportEventItem,
  TimelineGreetingItem,
  TimelineWaitingItem,
} from "@/components/features/chat/timeline";

function renderTimelineItem(item: TimelineItem) {
  switch (item.type) {
    case "user.message":
      return <TimelineUserMessageItem key={item.id} item={item} />;

    case "llm.call.cluster":
      return <LLMCallCluster key={item.id} item={item} isStreaming={isStreaming} />;

    case "tool.call":
      return <TimelineToolCallItem key={item.id} item={item} />;

    case "error":
      return <TimelineErrorItem key={item.id} item={item} />;

    case "support.event":
      return <TimelineSupportEventItem key={item.id} item={item} />;

    case "greeting":
      return <TimelineGreetingItem key={item.id} item={item} />;

    case "waiting":
      return <TimelineWaitingItem key={item.id} item={item} />;

    case "final":
    case "memory.event":
      return null;  // 不渲染

    default:
      return null;
  }
}
```

**Timeline Item 类型说明：**

| 类型 | 说明 | 组件 |
|-----|------|------|
| `user.message` | 用户消息 | `TimelineUserMessageItem` |
| `llm.call.cluster` | AI 回复（含推理/内容/商品） | `LLMCallCluster` |
| `tool.call` | 工具调用 | `TimelineToolCallItem` |
| `error` | 错误 | `TimelineErrorItem` |
| `greeting` | 欢迎语 | `TimelineGreetingItem` |
| `waiting` | 等待中 | `TimelineWaitingItem` |
| `support.event` | 客服事件 | `TimelineSupportEventItem` |
| `final` | 完成标记 | 不渲染 |
| `memory.event` | 记忆事件 | 不渲染 |

---

### 4. 输入区域：`ChatRichInput`

富文本输入框，支持 Markdown 格式。

```tsx
import { ChatRichInput } from "@/components/features/chat/ChatRichInput";

function InputArea() {
  const [prompt, setPrompt] = useState("");
  const sendMessage = useChatStore((s) => s.sendMessage);
  const abortStream = useChatStore((s) => s.abortStream);
  const isStreaming = useChatStore((s) => s.isStreaming);

  const handleSubmit = () => {
    if (isStreaming) {
      abortStream();
    } else {
      if (!prompt.trim()) return;
      sendMessage(prompt.trim());
      setPrompt("");
    }
  };

  return (
    <ChatRichInput
      value={prompt}
      onValueChange={setPrompt}
      onSubmit={handleSubmit}
      placeholder="输入消息..."
      isLoading={isStreaming}
      showToolbar={true}  // 显示格式化工具栏
    />
  );
}
```

**ChatRichInput Props：**

| Prop | 类型 | 说明 |
|-----|------|------|
| `value` | `string` | 输入内容（Markdown） |
| `onValueChange` | `(value: string) => void` | 内容变化回调 |
| `onSubmit` | `() => void` | 提交回调 |
| `placeholder` | `string` | 占位符 |
| `isLoading` | `boolean` | 加载状态（显示停止按钮） |
| `showToolbar` | `boolean` | 是否显示格式化工具栏 |
| `imageButton` | `ReactNode` | 图片上传按钮插槽 |

---

## 完整示例

### 简化版聊天室

```tsx
"use client";

import { useState, useEffect } from "react";
import {
  ChatContainerRoot,
  ChatContainerContent,
} from "@/components/prompt-kit/chat-container";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { ChatRichInput } from "@/components/features/chat/ChatRichInput";
import { useChatStore } from "@/stores";

export function SimpleChatRoom({ conversationId }: { conversationId: string }) {
  const [prompt, setPrompt] = useState("");

  // 从 Store 获取状态
  const timeline = useChatStore((s) => s.timelineState.timeline);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const abortStream = useChatStore((s) => s.abortStream);
  const loadMessages = useChatStore((s) => s.loadMessages);

  // 加载历史消息
  useEffect(() => {
    if (conversationId) {
      loadMessages(conversationId);
    }
  }, [conversationId, loadMessages]);

  const handleSubmit = () => {
    if (isStreaming) {
      abortStream();
    } else if (prompt.trim()) {
      sendMessage(prompt.trim());
      setPrompt("");
    }
  };

  return (
    <div className="flex h-screen flex-col">
      {/* 消息区域 */}
      <div className="relative flex-1 overflow-y-auto">
        <ChatContainerRoot className="h-full">
          <ChatContainerContent className="space-y-3 p-4">
            {timeline.map((item) => (
              <div key={item.id}>
                {/* 根据 item.type 渲染不同组件 */}
              </div>
            ))}
          </ChatContainerContent>
          <div className="absolute bottom-4 right-4">
            <ScrollButton />
          </div>
        </ChatContainerRoot>
      </div>

      {/* 输入区域 */}
      <div className="border-t p-4">
        <ChatRichInput
          value={prompt}
          onValueChange={setPrompt}
          onSubmit={handleSubmit}
          isLoading={isStreaming}
        />
      </div>
    </div>
  );
}
```

---

## WebSocket 人工客服模式

### 集成 WebSocket

```tsx
import { useUserWebSocket } from "@/hooks/use-websocket";

function ChatAppWithWebSocket() {
  const conversationId = "conv_123";
  const userId = "user_456";

  // WebSocket 连接
  const { isConnected, sendMessage: wsSendMessage } = useUserWebSocket({
    conversationId,
    userId,
    onMessage: (message) => {
      // 处理 WebSocket 消息
      if (message.action === "server.message") {
        // 添加到 timeline
      }
    },
  });

  // 判断是否人工模式
  const isHumanMode = useChatStore((s) => s.isHumanMode);

  const handleSendMessage = (content: string) => {
    if (isHumanMode && isConnected) {
      // 人工模式：通过 WebSocket 发送
      useChatStore.getState().addUserMessageOnly(content);
      wsSendMessage("client.user.send_message", { content });
    } else {
      // AI 模式：通过 API 发送
      useChatStore.getState().sendMessage(content);
    }
  };

  return (
    <ChatContent
      isHumanMode={isHumanMode}
      wsConnected={isConnected}
      wsSendMessage={(content) => wsSendMessage("client.user.send_message", { content })}
    />
  );
}
```

---

## 滚动行为详解

### 自动滚动触发时机

| 场景 | 是否自动滚动 |
|-----|------------|
| 发送新消息 | ✅ 是 |
| 收到流式响应 | ✅ 是（如果已在底部） |
| 用户向上滚动查看历史 | ❌ 否（保持位置） |
| 点击 ScrollButton | ✅ 是（平滑滚动） |

### 自定义滚动行为

```tsx
import { useStickToBottomContext } from "use-stick-to-bottom";

function CustomScrollControl() {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();

  // 强制滚动到底部
  const handleScrollToBottom = () => {
    scrollToBottom("smooth");  // 或 "instant"
  };

  return (
    <div>
      <p>是否在底部: {isAtBottom ? "是" : "否"}</p>
      <button onClick={handleScrollToBottom}>滚动到底部</button>
    </div>
  );
}
```

---

## 依赖清单

```json
{
  "dependencies": {
    "@embedease/chat-sdk": "workspace:*",
    "@embedease/chat-sdk-react": "workspace:*",
    "use-stick-to-bottom": "^1.1.1",
    "zustand": "^5.0.9",
    "@tiptap/react": "^2.x",
    "lucide-react": "^0.x"
  }
}
```

---

## 目录结构参考

```
frontend/
├── components/
│   ├── prompt-kit/
│   │   ├── chat-container.tsx    # 聊天容器（自动滚动）
│   │   ├── scroll-button.tsx     # 滚动按钮
│   │   └── message.tsx           # 消息包装器
│   └── features/chat/
│       ├── ChatContent.tsx       # 聊天主内容
│       ├── ChatRichInput.tsx     # 富文本输入
│       └── timeline/             # Timeline Item 组件
│           ├── LLMCallCluster.tsx
│           ├── TimelineUserMessageItem.tsx
│           └── ...
├── stores/
│   └── chat-store.ts             # 聊天状态管理
├── hooks/
│   └── use-websocket.ts          # WebSocket Hook
└── packages/
    ├── chat-sdk/                 # 核心 SDK
    └── chat-sdk-react/           # React Hooks
```

---

## 常见问题

### Q: 消息发送后没有自动滚动？

确保使用了 `ChatContainerRoot` 和 `ChatContainerContent` 包裹消息列表。

### Q: 如何在流式响应时显示打字指示器？

检查 `isStreaming` 状态，在最后一条消息后添加打字指示器：

```tsx
{isStreaming && <TypingIndicator />}
```

### Q: 如何处理图片上传？

使用 `ChatRichInput` 的 `imageButton` 插槽：

```tsx
<ChatRichInput
  imageButton={
    <ImageUploadButton onUpload={(images) => setImages(images)} />
  }
/>
```

### Q: 如何切换 AI 模式和人工模式？

通过 `useChatStore.getState().setHumanMode(true/false)` 切换。

---

## 许可证

MIT
