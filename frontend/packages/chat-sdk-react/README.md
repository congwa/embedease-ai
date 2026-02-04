# @embedease/chat-sdk-react

React Hooks for Chat SDK，提供 React 组件中使用聊天功能的便捷方式。

## 与 `@embedease/chat-sdk` 的关系

```
@embedease/chat-sdk          ← 核心库（框架无关）
        │
        │ 依赖
        ▼
@embedease/chat-sdk-react    ← React 绑定（本包）
        │
        │ 使用
        ▼
   你的 React 应用
```

| 使用场景 | 推荐方式 |
|---------|---------|
| **React 项目（推荐）** | 只安装 `@embedease/chat-sdk-react`，内部已包含核心 SDK |
| **需要底层 API** | 混用两个包，直接调用 `ChatClient` 等底层类 |
| **非 React 项目** | 只用 `@embedease/chat-sdk` |

**大多数 React 项目只需要本包**，核心 SDK 会作为依赖自动安装。

---

## 安装

```bash
pnpm add @embedease/chat-sdk-react
```

## 依赖

- `@embedease/chat-sdk` - 核心 SDK（自动安装）
- `react` >= 18.0.0

---

## 快速开始

### 基础使用

```tsx
import { useChat } from '@embedease/chat-sdk-react';

function ChatComponent() {
  const {
    timeline,
    isStreaming,
    sendMessage,
    abort,
  } = useChat({
    baseUrl: '/api',
    conversationId: 'conv_123',
    userId: 'user_456',
  });

  return (
    <div>
      {timeline.map((item) => (
        <div key={item.id}>{/* 渲染消息 */}</div>
      ))}
      {isStreaming && <button onClick={abort}>停止</button>}
      <button onClick={() => sendMessage('你好')}>发送</button>
    </div>
  );
}
```

---

## Hooks

### useChat

完整的聊天功能 Hook，整合 SSE 流式聊天、Timeline 状态管理和可选的 WebSocket 支持。

#### 选项

```typescript
interface UseChatOptions {
  /** API 基础 URL（必填） */
  baseUrl: string;

  /** WebSocket 基础 URL（可选，默认自动推断） */
  wsBaseUrl?: string;

  /** 会话 ID */
  conversationId?: string;

  /** 用户 ID */
  userId?: string;

  /** 初始消息列表 */
  initialMessages?: HistoryMessage[];

  /** 事件处理器 */
  onEvent?: (event: ChatEvent) => void;

  /** 错误处理器 */
  onError?: (error: Error) => void;

  /** 消息发送完成回调 */
  onComplete?: () => void;

  /** 是否启用 WebSocket（默认 false） */
  enableWebSocket?: boolean;

  /** WebSocket 消息处理器 */
  onWebSocketMessage?: (message: WSMessage) => void;

  /** 加载历史消息函数（用于 reload） */
  loadHistory?: () => Promise<HistoryMessage[]>;
}
```

#### 返回值

```typescript
interface UseChatReturn {
  /** 时间线项列表 */
  timeline: TimelineItem[];

  /** 完整 Timeline 状态 */
  state: TimelineState;

  /** 是否正在流式响应 */
  isStreaming: boolean;

  /** 是否正在加载 */
  isLoading: boolean;

  /** 错误信息 */
  error: Error | null;

  /** 发送消息 */
  sendMessage: (content: string, images?: ImageAttachment[]) => Promise<void>;

  /** 中止当前流 */
  abort: () => void;

  /** 清空所有消息 */
  clearMessages: () => void;

  /** 从历史消息初始化 */
  initFromHistory: (messages: HistoryMessage[]) => void;

  /** 重新加载历史消息（需配合 loadHistory 选项） */
  reload: () => Promise<void>;

  /** 当前 Turn ID */
  currentTurnId: string | null;

  /** 设置 Timeline 状态 */
  setState: (state: TimelineState) => void;

  /** WebSocket 是否已连接 */
  wsConnected: boolean;

  /** 发送 WebSocket 消息 */
  wsSendMessage: (action: string, payload: Record<string, unknown>) => void;
}
```

#### 完整示例

```tsx
import { useChat } from '@embedease/chat-sdk-react';
import { useState } from 'react';

function ChatPage() {
  const [input, setInput] = useState('');

  const {
    timeline,
    isStreaming,
    isLoading,
    error,
    sendMessage,
    abort,
    clearMessages,
    reload,
    wsConnected,
    wsSendMessage,
  } = useChat({
    baseUrl: '/api',
    conversationId: 'conv_123',
    userId: 'user_456',
    enableWebSocket: true,
    onEvent: (event) => {
      console.log('Event:', event.type);
    },
    onError: (err) => {
      console.error('Error:', err);
    },
    onWebSocketMessage: (msg) => {
      console.log('WS Message:', msg.action);
    },
    loadHistory: async () => {
      const res = await fetch('/api/messages');
      return res.json();
    },
  });

  const handleSend = async () => {
    if (!input.trim()) return;
    await sendMessage(input);
    setInput('');
  };

  return (
    <div>
      <div>WS: {wsConnected ? '已连接' : '未连接'}</div>

      {error && <div className="error">{error.message}</div>}

      <div className="messages">
        {timeline.map((item) => (
          <MessageItem key={item.id} item={item} />
        ))}
      </div>

      <div className="actions">
        <button onClick={reload} disabled={isLoading}>刷新</button>
        <button onClick={clearMessages}>清空</button>
      </div>

      <div className="input">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button onClick={abort}>停止</button>
        ) : (
          <button onClick={handleSend}>发送</button>
        )}
      </div>
    </div>
  );
}
```

---

### useTimeline

独立的 Timeline 状态管理 Hook，适用于需要自定义聊天逻辑的场景。

#### 选项

```typescript
interface UseTimelineOptions {
  /** 初始状态 */
  initialState?: TimelineState;
}
```

#### 返回值

```typescript
interface UseTimelineReturn {
  /** 当前状态 */
  state: TimelineState;

  /** 时间线项列表 */
  timeline: TimelineItem[];

  /** 处理事件 */
  dispatch: (event: ChatEvent) => void;

  /** 添加用户消息 */
  addUserMessage: (id: string, content: string, images?: ImageAttachment[]) => void;

  /** 开始助手回复 */
  startAssistantTurn: (turnId: string) => void;

  /** 清除 Turn */
  clearTurn: (turnId: string) => void;

  /** 结束 Turn */
  endTurn: () => void;

  /** 重置状态 */
  reset: () => void;

  /** 从历史消息初始化 */
  initFromHistory: (messages: HistoryMessage[]) => void;

  /** 设置状态 */
  setState: (state: TimelineState) => void;

  /** 当前 Turn ID */
  currentTurnId: string | null;

  /** 是否正在流式响应 */
  isStreaming: boolean;
}
```

#### 示例

```tsx
import { useTimeline } from '@embedease/chat-sdk-react';
import { ChatClient } from '@embedease/chat-sdk';

function CustomChat() {
  const {
    timeline,
    dispatch,
    addUserMessage,
    startAssistantTurn,
    endTurn,
    isStreaming,
  } = useTimeline();

  const sendMessage = async (content: string) => {
    const userMsgId = crypto.randomUUID();
    const turnId = crypto.randomUUID();

    addUserMessage(userMsgId, content);
    startAssistantTurn(turnId);

    const client = new ChatClient({ baseUrl: '/api' });

    for await (const event of client.stream({
      user_id: 'user_123',
      conversation_id: 'conv_456',
      message: content,
    })) {
      dispatch(event);
    }

    endTurn();
  };

  return (
    <div>
      {timeline.map((item) => (
        <div key={item.id}>{/* 渲染 */}</div>
      ))}
    </div>
  );
}
```

---

### useWebSocket

独立的 WebSocket 连接管理 Hook。

#### 选项

```typescript
interface UseWebSocketOptions {
  /** WebSocket 基础 URL（可选，默认自动推断） */
  baseUrl?: string;

  /** 会话 ID（必填） */
  conversationId: string | null;

  /** 用户/客服 ID（必填） */
  userId: string | null;

  /** 是否启用（默认 true） */
  enabled?: boolean;

  /** 角色类型（默认 'user'） */
  role?: 'user' | 'agent';

  /** 消息处理器 */
  onMessage?: (message: WSMessage) => void;

  /** 状态变更处理器 */
  onStateChange?: (state: ConnectionState, prevState: ConnectionState) => void;

  /** 错误处理器 */
  onError?: (error: Error) => void;
}
```

#### 返回值

```typescript
interface UseWebSocketReturn {
  /** 连接状态 */
  connectionState: ConnectionState;

  /** 是否已连接 */
  isConnected: boolean;

  /** 连接 ID */
  connectionId: string | null;

  /** 发送消息 */
  sendMessage: (action: string, payload: Record<string, unknown>) => string;

  /** 手动重连 */
  reconnect: () => void;

  /** 断开连接 */
  disconnect: () => void;
}
```

#### 示例

```tsx
import { useWebSocket } from '@embedease/chat-sdk-react';

function LiveChat() {
  const {
    isConnected,
    connectionId,
    sendMessage,
    reconnect,
  } = useWebSocket({
    conversationId: 'conv_123',
    userId: 'user_456',
    onMessage: (msg) => {
      if (msg.action === 'server.message') {
        // 处理收到的消息
        console.log('收到消息:', msg.payload);
      }
    },
    onStateChange: (state, prevState) => {
      console.log(`连接状态: ${prevState} -> ${state}`);
    },
  });

  const handleTyping = () => {
    sendMessage('client.typing', { is_typing: true });
  };

  return (
    <div>
      <div>状态: {isConnected ? '已连接' : '断开'}</div>
      <div>连接 ID: {connectionId}</div>
      <button onClick={reconnect}>重连</button>
      <input onFocus={handleTyping} />
    </div>
  );
}
```

---

## 配置说明

### 环境变量

```bash
# WebSocket 基础 URL（可选）
NEXT_PUBLIC_WS_URL=wss://api.example.com

# 使用新 SDK（默认 true）
NEXT_PUBLIC_USE_NEW_CHAT_SDK=true
```

### WebSocket URL 推断规则

当未指定 `wsBaseUrl` 时，自动推断：

1. 优先使用 `NEXT_PUBLIC_WS_URL` 环境变量
2. 开发环境默认 `ws://127.0.0.1:8000`
3. 生产环境根据 `baseUrl` 推断协议和主机

---

## 类型导出

本包重新导出了核心 SDK 的常用类型：

```typescript
import {
  type TimelineState,
  type TimelineItem,
  type ChatEvent,
  type ChatRequest,
  type ImageAttachment,
  type HistoryMessage,
  type ConnectionState,
  type WSMessage,
} from '@embedease/chat-sdk-react';
```

---

## 错误处理

### SSE 错误

```tsx
const { error, sendMessage } = useChat({ ... });

// 错误会自动更新到 error 状态
if (error) {
  return <div className="error">{error.message}</div>;
}

// 或者使用 onError 回调
useChat({
  onError: (err) => {
    toast.error(err.message);
  },
});
```

### WebSocket 错误

```tsx
useWebSocket({
  onError: (err) => {
    console.error('WebSocket 错误:', err);
  },
});
```

---

## 最佳实践

### 1. 会话和用户 ID

确保在组件挂载时提供有效的 `conversationId` 和 `userId`：

```tsx
function ChatWrapper() {
  const { conversationId, userId } = useAuth();

  if (!conversationId || !userId) {
    return <Loading />;
  }

  return (
    <ChatComponent
      conversationId={conversationId}
      userId={userId}
    />
  );
}
```

### 2. 历史消息加载

使用 `initialMessages` 或 `loadHistory` 加载历史：

```tsx
// 方式 1: 初始消息
const { data: messages } = useSWR('/api/messages');
const chat = useChat({
  initialMessages: messages,
  // ...
});

// 方式 2: 动态加载
const chat = useChat({
  loadHistory: async () => {
    const res = await fetch('/api/messages');
    return res.json();
  },
});

// 手动刷新
<button onClick={chat.reload}>刷新</button>
```

### 3. 图片上传

```tsx
const [images, setImages] = useState<ImageAttachment[]>([]);

const handleUpload = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch('/api/upload', { method: 'POST', body: formData });
  const image = await res.json();
  setImages((prev) => [...prev, image]);
};

const handleSend = () => {
  sendMessage(input, images);
  setImages([]);
};
```

### 4. 客服系统

```tsx
// 用户端
const userChat = useChat({
  enableWebSocket: true,
  onWebSocketMessage: (msg) => {
    if (msg.action === 'server.handoff_started') {
      // 转人工
    }
  },
});

// 客服端
const agentWs = useWebSocket({
  role: 'agent',
  conversationId,
  userId: agentId,
});
```

### 5. 混用两个包（高度定制）

当 `useChat` 不够灵活时，可以混用 `@embedease/chat-sdk` 和本包：

```tsx
import { useTimeline } from '@embedease/chat-sdk-react';
import { ChatClient } from '@embedease/chat-sdk';  // 直接使用核心库

function CustomChat() {
  const {
    timeline,
    dispatch,
    addUserMessage,
    startAssistantTurn,
    endTurn,
  } = useTimeline();

  const sendMessage = async (content: string) => {
    const userMsgId = crypto.randomUUID();
    const turnId = crypto.randomUUID();

    // 手动管理 Timeline 状态
    addUserMessage(userMsgId, content);
    startAssistantTurn(turnId);

    // 直接使用底层 ChatClient
    const client = new ChatClient({ baseUrl: '/api' });
    for await (const event of client.stream({
      user_id: 'user_123',
      conversation_id: 'conv_456',
      message: content,
    })) {
      dispatch(event);  // 手动派发事件到 Timeline
    }

    endTurn();
  };

  return (
    <div>
      {timeline.map((item) => (
        <div key={item.id}>{/* 渲染 */}</div>
      ))}
      <button onClick={() => sendMessage('你好')}>发送</button>
    </div>
  );
}
```

**适用场景**：需要自定义流式处理逻辑、多 Client 实例、特殊错误处理等。

---

## 构建

```bash
pnpm build      # 构建
pnpm dev        # 开发模式
pnpm typecheck  # 类型检查
pnpm clean      # 清理
```

---

## 许可证

MIT
