# @embedease/chat-sdk

前端 Chat SDK 核心包，提供框架无关的聊天功能实现。

## 与 `@embedease/chat-sdk-react` 的关系

| 包 | 适用场景 | 说明 |
|---|---------|------|
| `@embedease/chat-sdk` | 非 React 项目（Vue/Svelte/原生 JS） | 框架无关的核心库 |
| `@embedease/chat-sdk-react` | React 项目 | 封装了本包的 React Hooks |

**React 项目推荐直接使用 `@embedease/chat-sdk-react`**，它内部已依赖本包，无需单独安装。

**非 React 项目** 或需要 **高度定制** 时，直接使用本包。

---

## 安装

```bash
pnpm add @embedease/chat-sdk
```

## 特性

- 🚀 **框架无关** - 核心逻辑不依赖 React/Vue，可在任何环境使用
- 📡 **SSE 流式聊天** - 支持实时流式响应
- 🔄 **Timeline 状态管理** - 完整的聊天消息状态管理
- 🌐 **WebSocket 支持** - 实时双向通信
- 📦 **TypeScript** - 完整的类型定义

---

## 快速开始

### 基础流式聊天

```typescript
import { ChatClient } from '@embedease/chat-sdk';

const client = new ChatClient({
  baseUrl: 'https://api.example.com',
});

// 发送消息并接收流式响应
for await (const event of client.stream({
  user_id: 'user_123',
  conversation_id: 'conv_456',
  message: '你好',
})) {
  console.log(event.type, event.payload);
}
```

### 带 Timeline 状态管理

```typescript
import {
  ChatClient,
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  timelineReducer,
  endTurn,
} from '@embedease/chat-sdk';

const client = new ChatClient({ baseUrl: 'https://api.example.com' });

// 初始化状态
let state = createInitialState();

// 添加用户消息
state = addUserMessage(state, 'msg_1', '你好');
state = startAssistantTurn(state, 'turn_1');

// 流式聊天，自动更新状态
for await (const event of client.stream({
  user_id: 'user_123',
  conversation_id: 'conv_456',
  message: '你好',
})) {
  state = timelineReducer(state, event);
  console.log('Timeline:', state.timeline);
}

state = endTurn(state);
```

### 使用 streamWithTimeline（推荐）

```typescript
import { ChatClient } from '@embedease/chat-sdk';

const client = new ChatClient({ baseUrl: 'https://api.example.com' });

const { events, getTimeline, abort } = client.streamWithTimeline({
  user_id: 'user_123',
  conversation_id: 'conv_456',
  message: '你好',
});

// 流式处理事件
for await (const event of events) {
  console.log(event.type);
  // 随时获取最新状态
  console.log('当前 Timeline:', getTimeline().timeline);
}

// 或者中止流
// abort();
```

---

## API 参考

### ChatClient

主入口类，封装 SSE 流式聊天功能。

#### 构造函数

```typescript
new ChatClient(config: {
  baseUrl: string;          // API 基础 URL
  headers?: Record<string, string>;  // 自定义请求头
})
```

#### 方法

##### `stream(request: ChatRequest): AsyncGenerator<ChatEvent>`

发送消息并获取流式响应。

```typescript
interface ChatRequest {
  user_id: string;
  conversation_id: string;
  message: string;
  images?: ImageAttachment[];
}
```

##### `streamWithTimeline(request, options?): StreamWithTimelineResult`

发送消息并获取流式响应，带 Timeline 状态管理。

```typescript
interface StreamWithTimelineResult {
  events: AsyncGenerator<ChatEvent>;
  getTimeline: () => TimelineState;
  abort: () => void;
}

// 可选配置
interface Options {
  initialState?: TimelineState;   // 初始状态
  userMessageId?: string;         // 用户消息 ID
  assistantTurnId?: string;       // 助手 Turn ID
}
```

##### `abort(): void`

中止当前流。

---

### Timeline 模块

状态管理函数，处理聊天消息的增删改查。

#### 创建和初始化

```typescript
import {
  createInitialState,
  historyToTimeline,
} from '@embedease/chat-sdk';

// 创建空状态
const state = createInitialState();

// 从历史消息初始化
const stateFromHistory = historyToTimeline(messages);
```

#### Action 函数

```typescript
import {
  addUserMessage,
  addGreetingMessage,
  startAssistantTurn,
  clearTurn,
  endTurn,
} from '@embedease/chat-sdk';

// 添加用户消息
state = addUserMessage(state, id, content, images?);

// 添加欢迎语
state = addGreetingMessage(state, {
  id: 'greeting_1',
  body: '欢迎使用',
  title?: '标题',
  cta?: { text: '开始', payload: 'start' },
});

// 开始助手回复
state = startAssistantTurn(state, turnId);

// 清除某个 Turn
state = clearTurn(state, turnId);

// 结束当前 Turn
state = endTurn(state);
```

#### Reducer

```typescript
import { timelineReducer } from '@embedease/chat-sdk';

// 处理事件
state = timelineReducer(state, event);
```

---

### WebSocket 模块

实时双向通信支持。

#### 创建管理器

```typescript
import {
  createUserWebSocketManager,
  createAgentWebSocketManager,
} from '@embedease/chat-sdk';

// 用户端
const userWs = createUserWebSocketManager(
  'wss://api.example.com',
  'conv_123',
  'user_456'
);

// 客服端
const agentWs = createAgentWebSocketManager(
  'wss://api.example.com',
  'conv_123',
  'agent_789'
);
```

#### WebSocketManager 方法

```typescript
// 连接
manager.connect();

// 断开
manager.disconnect();

// 发送消息
const msgId = manager.send('action.name', { key: 'value' });

// 监听消息
const unsubscribe = manager.onMessage((msg) => {
  console.log(msg.action, msg.payload);
});

// 监听状态变化
manager.onStateChange((state, prevState) => {
  console.log(`${prevState} -> ${state}`);
});

// 监听错误
manager.onError((error) => {
  console.error(error);
});

// 获取状态
manager.getState();        // 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
manager.isConnected();     // boolean
manager.getConnectionId(); // string | null
manager.getConversationId(); // string | null

// 销毁
manager.destroy();
```

---

### 类型定义

#### ChatEvent

所有 SSE 事件的联合类型。

```typescript
type ChatEventType =
  | 'meta.start'
  | 'llm.call.start'
  | 'llm.call.end'
  | 'assistant.reasoning.delta'
  | 'assistant.delta'
  | 'assistant.products'
  | 'assistant.todos'
  | 'assistant.final'
  | 'tool.start'
  | 'tool.end'
  | 'error'
  | 'context.summarized'
  | 'memory.extraction.start'
  | 'memory.extraction.complete'
  | 'memory.profile.updated'
  | 'skill.activated'
  | 'skill.loaded'
  | 'support.*';

interface ChatEvent {
  seq: number;
  type: ChatEventType;
  payload: ChatEventPayload;
}
```

#### TimelineItem

时间线项类型。

```typescript
type TimelineItem =
  | UserMessageItem      // 用户消息
  | LLMCallClusterItem   // LLM 调用集群
  | ToolCallItem         // 工具调用
  | ErrorItem            // 错误
  | FinalItem            // 完成
  | GreetingItem         // 欢迎语
  | WaitingItem          // 等待中
  | SkillActivatedItem   // 技能激活
  | SupportEventItem     // 客服事件
  | MemoryEventItem;     // 记忆事件
```

#### TimelineState

```typescript
interface TimelineState {
  timeline: TimelineItem[];
  indexById: Record<string, number>;
  activeTurn: {
    turnId: string | null;
    currentLlmCallId: string | null;
    currentToolCallId: string | null;
    isStreaming: boolean;
  };
}
```

---

## 事件处理

### 自定义事件处理

```typescript
import { ChatClient } from '@embedease/chat-sdk';

for await (const event of client.stream(request)) {
  switch (event.type) {
    case 'assistant.delta':
      // 增量文本
      console.log(event.payload.delta);
      break;

    case 'assistant.reasoning.delta':
      // 推理过程
      console.log('[Thinking]', event.payload.delta);
      break;

    case 'tool.start':
      // 工具开始
      console.log('Tool:', event.payload.name);
      break;

    case 'tool.end':
      // 工具结束
      console.log('Tool done:', event.payload.status);
      break;

    case 'assistant.products':
      // 商品推荐
      console.log('Products:', event.payload.items);
      break;

    case 'error':
      // 错误
      console.error(event.payload.message);
      break;

    case 'assistant.final':
      // 完成
      console.log('Final:', event.payload.content);
      break;
  }
}
```

### 类型判断辅助函数

```typescript
import {
  isLLMCallInternalEvent,
  isToolCallEvent,
  isDataEvent,
} from '@embedease/chat-sdk';

if (isLLMCallInternalEvent(event.type)) {
  // 处理 LLM 调用内部事件
}

if (isToolCallEvent(event.type)) {
  // 处理工具调用事件
}

if (isDataEvent(event.type)) {
  // 处理数据事件
}
```

---

## 错误处理

### SSE 错误

```typescript
try {
  for await (const event of client.stream(request)) {
    // ...
  }
} catch (error) {
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      console.log('用户取消');
    } else {
      console.error('SSE 错误:', error.message);
    }
  }
}
```

### 中止流

```typescript
const client = new ChatClient({ baseUrl });

// 开始流式请求
const streamPromise = (async () => {
  for await (const event of client.stream(request)) {
    // ...
  }
})();

// 5 秒后中止
setTimeout(() => {
  client.abort();
}, 5000);
```

---

## 高级配置

### 自定义请求头

```typescript
const client = new ChatClient({
  baseUrl: 'https://api.example.com',
  headers: {
    'Authorization': 'Bearer token',
    'X-Custom-Header': 'value',
  },
});
```

### WebSocket 配置

```typescript
import { WebSocketManager } from '@embedease/chat-sdk';

const manager = new WebSocketManager({
  baseUrl: 'wss://api.example.com',
  endpoint: '/ws/user/conv_123',
  token: 'user_token',
  pingInterval: 30000,      // 心跳间隔
  pongTimeout: 10000,       // 心跳超时
  maxReconnectAttempts: 10, // 最大重连次数
  initialReconnectDelay: 1000, // 初始重连延迟
  maxReconnectDelay: 30000,    // 最大重连延迟
});
```

---

## 与旧 SDK 共存

本 SDK 支持通过 Adapter 层与旧 SDK 共存，通过环境变量切换：

```bash
# 使用新 SDK（默认）
NEXT_PUBLIC_USE_NEW_CHAT_SDK=true

# 回退到旧 SDK
NEXT_PUBLIC_USE_NEW_CHAT_SDK=false
```

---

## 构建

```bash
# 构建
pnpm build

# 开发模式（监听变化）
pnpm dev

# 类型检查
pnpm typecheck

# 清理
pnpm clean
```

---

## 许可证

MIT
