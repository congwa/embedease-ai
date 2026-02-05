# LangGraph Agent Kit

> 统一的流式聊天 Agent 框架 - 提供事件协议、上下文管理、中间件系统和工具管理

## 目录

- [快速开始](#快速开始)
- [安装](#安装)
- [核心概念](#核心概念)
- [API 参考](#api-参考)
  - [ChatStreamKit](#chatstreamkit)
  - [事件系统](#事件系统)
  - [Payload TypedDict](#payload-typeddict)
  - [上下文管理](#上下文管理)
  - [Chat Models](#chat-models)
  - [Content Parser](#content-parser)
  - [StreamingResponseHandler](#streamingresponsehandler)
  - [中间件](#中间件)
  - [工具](#工具)
  - [SSE 编码](#sse-编码)
  - [FastAPI 集成](#fastapi-集成)
- [使用场景](#使用场景)
- [事件类型参考](#事件类型参考)

---

## 快速开始

### 基础用法：使用 ChatStreamKit

```python
from langchain_openai import ChatOpenAI
from langgraph_agent_kit import ChatStreamKit, Middlewares

# 1. 创建模型
model = ChatOpenAI(model="gpt-4o-mini")

# 2. 创建 Kit
kit = ChatStreamKit(
    model=model,
    middlewares=[Middlewares.sse_events()],
)

# 3. 流式聊天
async for event in kit.chat_stream(
    message="你好，请介绍一下自己",
    conversation_id="conv_123",
    user_id="user_456",
):
    print(f"[{event.type}] {event.payload}")
```

### FastAPI 集成

```python
from fastapi import FastAPI, Request
from langchain_openai import ChatOpenAI
from langgraph_agent_kit import ChatStreamKit, Middlewares

app = FastAPI()
model = ChatOpenAI(model="gpt-4o-mini")
kit = ChatStreamKit(model=model, middlewares=[Middlewares.sse_events()])

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    return kit.create_sse_response(
        message=data["message"],
        conversation_id=data["conversation_id"],
        user_id=data["user_id"],
    )
```

---

## 安装

### 作为本地 uv workspace 包

```toml
# backend/pyproject.toml
[project]
dependencies = [
    "langgraph-agent-kit",
]

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
langgraph-agent-kit = { workspace = true }
```

### 同步依赖

```bash
uv sync
```

---

## 核心概念

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      ChatStreamKit                          │
│  - 主入口类                                                  │
│  - 管理模型/Agent、中间件、工具                               │
│  - 提供 chat_stream() 和 create_sse_response()               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   事件处理流程                               │
│  1. 创建 QueueDomainEmitter 和 ChatContext                  │
│  2. 启动 Agent/Model 生成任务                                │
│  3. 消费 domain events → 转换为 StreamEvent                  │
│  4. 通过 SSE 推送给客户端                                    │
└─────────────────────────────────────────────────────────────┘
```

### 事件流

```
meta.start → llm.call.start → [assistant.delta...] → llm.call.end 
           → tool.start → tool.end → assistant.final
```

---

## API 参考

### ChatStreamKit

主入口类，提供流畅的 API 配置和运行流式聊天。

#### 构造函数

```python
ChatStreamKit(
    *,
    model: Any = None,           # LangChain 模型实例
    agent: Any = None,           # LangGraph Agent 实例（优先级高于 model）
    middlewares: list = None,    # 中间件列表
    tools: list = None,          # 工具列表
    event_queue_size: int = 10000,  # 事件队列大小
)
```

#### 方法

##### `chat_stream()`

流式聊天，返回 `StreamEvent` 异步生成器。

```python
async def chat_stream(
    self,
    *,
    message: str,                     # 用户消息
    conversation_id: str,             # 会话 ID
    user_id: str,                     # 用户 ID
    assistant_message_id: str = None, # 助手消息 ID（自动生成）
    user_message_id: str = None,      # 用户消息 ID
    context_data: dict = None,        # 额外上下文数据
) -> AsyncGenerator[StreamEvent, None]:
```

**使用示例：**

```python
async for event in kit.chat_stream(
    message="你好",
    conversation_id="conv_123",
    user_id="user_456",
):
    if event.type == "assistant.delta":
        print(event.payload["delta"], end="", flush=True)
    elif event.type == "assistant.final":
        print(f"\n\n完整回复: {event.payload['content']}")
```

##### `create_sse_response()`

创建 FastAPI SSE 响应。

```python
def create_sse_response(
    self,
    *,
    message: str,
    conversation_id: str,
    user_id: str,
    **kwargs,
) -> StreamingResponse:
```

##### `add_middleware()`

链式添加中间件。

```python
kit = (ChatStreamKit(model=model)
    .add_middleware(Middlewares.sse_events())
    .add_middleware(Middlewares.logging()))
```

##### `add_tool()`

链式添加工具。

```python
from langgraph_agent_kit import ToolSpec

kit.add_tool(ToolSpec(
    name="search",
    description="搜索工具",
    func=search_function,
))
```

---

### 事件系统

#### StreamEventType

所有支持的事件类型枚举。

```python
from langgraph_agent_kit import StreamEventType

# 流级别事件
StreamEventType.META_START          # "meta.start"
StreamEventType.ASSISTANT_FINAL     # "assistant.final"
StreamEventType.ERROR               # "error"

# LLM 调用事件
StreamEventType.LLM_CALL_START      # "llm.call.start"
StreamEventType.LLM_CALL_END        # "llm.call.end"
StreamEventType.ASSISTANT_DELTA     # "assistant.delta"
StreamEventType.ASSISTANT_REASONING_DELTA  # "assistant.reasoning.delta"

# 工具调用事件
StreamEventType.TOOL_START          # "tool.start"
StreamEventType.TOOL_END            # "tool.end"

# 数据事件
StreamEventType.ASSISTANT_PRODUCTS  # "assistant.products"
StreamEventType.ASSISTANT_TODOS     # "assistant.todos"
StreamEventType.CONTEXT_SUMMARIZED  # "context.summarized"

# 记忆事件
StreamEventType.MEMORY_EXTRACTION_START    # "memory.extraction.start"
StreamEventType.MEMORY_EXTRACTION_COMPLETE # "memory.extraction.complete"
StreamEventType.MEMORY_PROFILE_UPDATED     # "memory.profile.updated"

# Supervisor 事件
StreamEventType.AGENT_ROUTED        # "agent.routed"
StreamEventType.AGENT_HANDOFF       # "agent.handoff"
StreamEventType.AGENT_COMPLETE      # "agent.complete"

# 中间件事件
StreamEventType.MODEL_RETRY_START   # "model.retry.start"
StreamEventType.MODEL_FALLBACK      # "model.fallback"
```

#### StreamEvent

事件数据模型。

```python
from langgraph_agent_kit import StreamEvent

# 字段
event.v              # 协议版本 (默认 1)
event.id             # 事件 ID (如 "evt_xxx")
event.seq            # 序号 (从 1 开始)
event.ts             # 时间戳 (毫秒)
event.conversation_id  # 会话 ID
event.message_id     # 助手消息 ID
event.type           # 事件类型 (如 "assistant.delta")
event.payload        # 事件载荷
```

#### make_event()

手动创建事件。

```python
from langgraph_agent_kit import make_event, StreamEventType

event = make_event(
    seq=1,
    conversation_id="conv_123",
    message_id="msg_456",
    type=StreamEventType.ASSISTANT_DELTA.value,
    payload={"delta": "你好"},
)
```

---

### Payload TypedDict

SDK 提供类型安全的 Payload 定义，支持 IDE 自动补全和类型检查。

```python
from langgraph_agent_kit import (
    MetaStartPayload,
    TextDeltaPayload,
    ToolStartPayload,
    ToolEndPayload,
    LlmCallStartPayload,
    LlmCallEndPayload,
    ErrorPayload,
    MemoryExtractionStartPayload,
    MemoryExtractionCompletePayload,
    MemoryProfileUpdatedPayload,
    TodoItem,
    TodosPayload,
    ContextSummarizedPayload,
    ContextTrimmedPayload,
    AgentRoutedPayload,
    AgentHandoffPayload,
    AgentCompletePayload,
    SkillActivatedPayload,
    SkillLoadedPayload,
    ModelRetryStartPayload,
    ModelRetryFailedPayload,
    ModelFallbackPayload,
    ModelCallLimitExceededPayload,
    ContextEditedPayload,
)
```

#### 常用 Payload 类型

| Payload | 字段 | 说明 |
|---------|------|------|
| `MetaStartPayload` | `user_message_id`, `assistant_message_id` | 流开始 |
| `TextDeltaPayload` | `delta` | 文本增量 |
| `ToolStartPayload` | `tool_call_id`, `name`, `input?` | 工具开始 |
| `ToolEndPayload` | `tool_call_id`, `name`, `status?`, `count?`, `error?` | 工具结束 |
| `LlmCallStartPayload` | `message_count`, `llm_call_id?` | LLM 调用开始 |
| `LlmCallEndPayload` | `elapsed_ms`, `error?` | LLM 调用结束 |
| `ErrorPayload` | `message`, `code?`, `detail?` | 错误信息 |
| `TodosPayload` | `todos: list[TodoItem]` | TODO 列表 |
| `ContextSummarizedPayload` | `messages_before`, `messages_after` | 上下文压缩 |

#### 使用示例

```python
from langgraph_agent_kit import ToolEndPayload

# 类型安全的 payload 构造
payload: ToolEndPayload = {
    "tool_call_id": "tc_123",
    "name": "search",
    "status": "success",
    "count": 10,
}
```

---

### 上下文管理

#### ChatContext

聊天上下文，在工具和中间件中传递。

```python
from langgraph_agent_kit import ChatContext

context = ChatContext(
    conversation_id="conv_123",
    user_id="user_456",
    assistant_message_id="msg_789",
    emitter=emitter,       # 事件发射器
    db=db_session,         # 数据库会话（可选）
)

# 获取数据库会话
db = context.get_db_session()
```

#### QueueDomainEmitter

事件发射器，用于在工具/中间件中发送事件。

```python
from langgraph_agent_kit import QueueDomainEmitter
import asyncio

loop = asyncio.get_running_loop()
queue = asyncio.Queue()
emitter = QueueDomainEmitter(queue=queue, loop=loop)

# 同步发射（线程安全）
emitter.emit("tool.progress", {"percent": 50})

# 异步发射（严格顺序）
await emitter.aemit("assistant.delta", {"delta": "你好"})
```

---

### Chat Models

SDK 提供统一的聊天模型基类和工厂函数，支持 v0/v1 双版本切换。

#### 版本说明

| 版本 | 说明 | 推理内容处理方式 |
|------|------|------------------|
| **v1（推荐）** | 使用 LangChain 标准 `content_blocks` | 直接从 `message.content` 按块类型分流 |
| **v0（兼容）** | 使用自定义 `ReasoningChunk` 结构 | 通过 `model.extract_reasoning()` 提取 |

#### create_chat_model()

统一的模型创建入口。

```python
from langgraph_agent_kit import create_chat_model

# 创建 v1 模型（默认）
model = create_chat_model(
    model="Qwen/Qwen3-8B",
    base_url="https://api.siliconflow.cn/v1",
    api_key="sk-xxx",
    provider="siliconflow",
    temperature=0.7,
)

# 创建 v0 兼容模型
model_v0 = create_chat_model(
    model="Qwen/Qwen3-8B",
    base_url="https://api.siliconflow.cn/v1",
    api_key="sk-xxx",
    provider="siliconflow",
    use_v0=True,  # 切换到 v0 兼容层
)
```

#### V1ChatModel

强制使用 LangChain v1 输出格式的模型基类。

```python
from langgraph_agent_kit import V1ChatModel, is_v1_model

# 直接使用
model = V1ChatModel(
    model="gpt-4o-mini",
    openai_api_base="https://api.openai.com/v1",
    openai_api_key="sk-xxx",
)

# 版本检测
if is_v1_model(model):
    # 使用 content_blocks 解析
    parsed = parse_content_blocks(message)
```

#### 提供商扩展

SDK 内置了 SiliconFlow 的推理模型支持：

```python
from langgraph_agent_kit import (
    SiliconFlowV1ChatModel,       # v1 版本
    SiliconFlowReasoningChatModel, # v0 版本
)

# SiliconFlow 推理模型（自动处理 reasoning_content）
model = SiliconFlowV1ChatModel(
    model="Qwen/QwQ-32B",
    openai_api_base="https://api.siliconflow.cn/v1",
    openai_api_key="sk-xxx",
)
```

#### 自定义提供商

通过注册表扩展其他提供商：

```python
from langgraph_agent_kit import V1_REASONING_MODEL_REGISTRY

# 注册新提供商
V1_REASONING_MODEL_REGISTRY["deepseek"] = (
    "my_package.providers.deepseek",
    "DeepSeekV1ChatModel",
)
```

---

### Content Parser

解析 LangChain v1 content_blocks 的工具函数。

#### parse_content_blocks()

```python
from langgraph_agent_kit import (
    parse_content_blocks,
    ParsedContent,
    is_text_block,
    is_reasoning_block,
    is_tool_call_block,
)

# 解析消息内容
parsed: ParsedContent = parse_content_blocks(message)

print(parsed.text)       # 合并后的文本
print(parsed.reasoning)  # 合并后的推理内容
print(parsed.tool_calls) # 工具调用列表
```

#### 类型守卫

```python
from langgraph_agent_kit import (
    ContentBlock,
    TextContentBlock,
    ReasoningContentBlock,
    ToolCallBlock,
    is_text_block,
    is_reasoning_block,
    is_tool_call_block,
    is_tool_call_chunk_block,
    is_image_block,
    get_block_type,
)

# 按块类型分流处理
for block in message.content:
    if is_text_block(block):
        print(f"文本: {block['text']}")
    elif is_reasoning_block(block):
        print(f"推理: {block['reasoning']}")
    elif is_tool_call_block(block):
        print(f"工具调用: {block['name']}")
```

#### ParsedContent 结构

```python
@dataclass
class ParsedContent:
    text: str              # 合并后的文本
    reasoning: str         # 合并后的推理
    tool_calls: list[dict] # 工具调用列表
    raw_blocks: list[dict] # 原始块列表
```

---

### StreamingResponseHandler

处理 LangGraph 流式输出的响应处理器，支持 v0/v1 双模式。

```python
from langgraph_agent_kit import StreamingResponseHandler

# 创建处理器
handler = StreamingResponseHandler(
    emitter=emitter,
    conversation_id="conv_123",
    model=model,    # 可选，用于版本检测
    mode="v1",      # "v1" | "v0" | "auto"
)

# 处理流式消息
async for msg in agent.astream(...):
    await handler.handle_message(msg)

# 获取最终结果
result = await handler.finalize()
print(result.full_content)
print(result.full_reasoning)
```

#### 自动版本检测

```python
# mode="auto" 时根据 model 自动检测版本
handler = StreamingResponseHandler(
    emitter=emitter,
    model=model,
    mode="auto",  # 如果 is_v1_model(model) 为 True 则使用 v1
)
```

#### 继承扩展

```python
from langgraph_agent_kit import StreamingResponseHandler

class MyHandler(StreamingResponseHandler):
    """添加商品数据处理"""
    
    products_data: list[dict] | None = None
    
    async def _handle_tool_message(self, msg):
        await super()._handle_tool_message(msg)
        # 提取商品数据
        self.products_data = extract_products(msg.content)
    
    async def finalize(self):
        result = await super().finalize()
        if self.products_data:
            await self.emitter.aemit("assistant.products", {"items": self.products_data})
        return result
```

---

### 中间件

#### MiddlewareSpec

中间件规格定义。

```python
from langgraph_agent_kit import MiddlewareSpec

middleware = MiddlewareSpec(
    name="my_middleware",
    order=50,              # 执行顺序（越小越先）
    enabled=True,
    before_model=my_before_model_func,
    after_model=my_after_model_func,
    before_tool=my_before_tool_func,
    after_tool=my_after_tool_func,
)
```

#### BaseMiddleware

中间件基类，继承实现自定义中间件。

```python
from langgraph_agent_kit import BaseMiddleware, MiddlewareConfig

class MyMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__(MiddlewareConfig(order=50))
    
    async def before_model(self, request, context):
        # 模型调用前的处理
        print(f"Before model call for {context.conversation_id}")
        return request
    
    async def after_model(self, response, context):
        # 模型调用后的处理
        print("After model call")
        return response
    
    async def before_tool(self, tool_call, context):
        # 工具调用前的处理
        return tool_call
    
    async def after_tool(self, tool_result, context):
        # 工具调用后的处理
        return tool_result
```

#### MiddlewareRegistry

中间件注册表。

```python
from langgraph_agent_kit import MiddlewareRegistry

registry = MiddlewareRegistry()
registry.register(my_middleware)
registry.unregister("my_middleware")

# 获取所有启用的中间件（按 order 排序）
middlewares = registry.get_all(enabled_only=True)
```

#### 内置中间件

```python
from langgraph_agent_kit import Middlewares

# SSE 事件推送中间件（发射 llm.call.start / llm.call.end）
sse_middleware = Middlewares.sse_events(order=30)

# 日志记录中间件
logging_middleware = Middlewares.logging(order=60)
```

---

### 工具

#### ToolSpec

工具规格定义。

```python
from langgraph_agent_kit import ToolSpec, ToolConfig

def search_products(query: str) -> str:
    return f"搜索结果: {query}"

tool = ToolSpec(
    name="search_products",
    description="搜索商品",
    func=search_products,
    config=ToolConfig(
        enabled=True,
        emit_events=True,
        timeout_seconds=30,
    ),
)
```

#### ToolRegistry

工具注册表。

```python
from langgraph_agent_kit import ToolRegistry

registry = ToolRegistry()
registry.register(tool)
registry.unregister("search_products")

# 获取所有启用的工具
tools = registry.get_all(enabled_only=True)

# 获取 LangChain 格式的工具列表
lc_tools = registry.get_langchain_tools()
```

#### @with_tool_events 装饰器

自动为工具添加 `tool.start` / `tool.end` 事件。

```python
from langgraph_agent_kit import with_tool_events

@with_tool_events()
async def my_tool(query: str, *, runtime) -> str:
    """搜索工具"""
    # 自动发射 tool.start
    result = await do_search(query)
    # 自动发射 tool.end
    return result

@with_tool_events(tool_name="custom_name", emit_input=True)
def sync_tool(data: dict, *, runtime) -> str:
    """同步工具，自定义名称，包含输入参数"""
    return process(data)
```

#### 在工具中手动发送事件

```python
from langgraph_agent_kit import (
    get_emitter_from_runtime,
    emit_tool_start,
    emit_tool_end,
)

async def my_tool(query: str, *, runtime) -> str:
    # 方式 1: 使用辅助函数
    emit_tool_start(runtime, "tc_123", "my_tool", {"query": query})
    result = await do_work()
    emit_tool_end(runtime, "tc_123", "my_tool", status="success", count=10)
    return result

async def another_tool(*, runtime) -> str:
    # 方式 2: 直接获取 emitter
    emitter = get_emitter_from_runtime(runtime)
    if emitter:
        emitter.emit("assistant.products", {"items": [...]})
    return "done"
```

---

### SSE 编码

#### encode_sse()

将事件编码为 SSE 数据帧。

```python
from langgraph_agent_kit import encode_sse, make_event

event = make_event(
    seq=1,
    conversation_id="conv_123",
    type="assistant.delta",
    payload={"delta": "你好"},
)

sse_data = encode_sse(event)
# 输出: 'data: {"v":1,"id":"evt_xxx","seq":1,...}\n\n'

# 也支持字典
sse_data = encode_sse({"type": "ping", "payload": {}})
```

---

### FastAPI 集成

#### create_sse_response()

从事件生成器创建 SSE 响应。

```python
from langgraph_agent_kit import create_sse_response
from fastapi import FastAPI

app = FastAPI()

@app.post("/chat")
async def chat():
    async def event_generator():
        # 产生 StreamEvent
        yield make_event(seq=1, conversation_id="xxx", type="meta.start", payload={})
        yield make_event(seq=2, conversation_id="xxx", type="assistant.delta", payload={"delta": "你好"})
        yield make_event(seq=3, conversation_id="xxx", type="assistant.final", payload={"content": "你好"})
    
    return create_sse_response(event_generator())
```

---

## 使用场景

### 场景 1: 简单聊天机器人

```python
from langchain_openai import ChatOpenAI
from langgraph_agent_kit import ChatStreamKit

model = ChatOpenAI(model="gpt-4o-mini")
kit = ChatStreamKit(model=model)

async def chat(message: str):
    async for event in kit.chat_stream(
        message=message,
        conversation_id="conv_1",
        user_id="user_1",
    ):
        if event.type == "assistant.delta":
            print(event.payload["delta"], end="", flush=True)
    print()
```

### 场景 2: 带工具的 Agent

```python
from langgraph_agent_kit import ChatStreamKit, ToolSpec, with_tool_events

@with_tool_events()
async def search_products(query: str, *, runtime) -> str:
    """搜索商品"""
    # 模拟搜索
    return f"找到 3 个商品: {query}"

kit = ChatStreamKit(
    agent=my_langgraph_agent,
    tools=[
        ToolSpec(
            name="search_products",
            description="搜索商品",
            func=search_products,
        )
    ],
)
```

### 场景 3: 自定义中间件

```python
from langgraph_agent_kit import (
    ChatStreamKit,
    BaseMiddleware,
    MiddlewareConfig,
    StreamEventType,
)

class TokenCountMiddleware(BaseMiddleware):
    """统计 Token 使用量"""
    
    def __init__(self):
        super().__init__(MiddlewareConfig(order=25))
        self.total_tokens = 0
    
    async def after_model(self, response, context):
        usage = getattr(response, "usage_metadata", None)
        if usage:
            self.total_tokens += usage.get("total_tokens", 0)
            emitter = getattr(context, "emitter", None)
            if emitter:
                await emitter.aemit(
                    "token.usage",
                    {"total": self.total_tokens},
                )
        return response

kit = ChatStreamKit(
    model=model,
    middlewares=[TokenCountMiddleware()],
)
```

### 场景 4: 在工具中推送进度

```python
from langgraph_agent_kit import get_emitter_from_runtime

async def long_running_task(*, runtime):
    """长时间运行的任务"""
    emitter = get_emitter_from_runtime(runtime)
    
    for i in range(100):
        await do_step(i)
        if emitter:
            emitter.emit("task.progress", {
                "percent": i + 1,
                "message": f"正在处理第 {i + 1} 步",
            })
    
    return "任务完成"
```

### 场景 5: 手动构建事件流

```python
import asyncio
from langgraph_agent_kit import (
    QueueDomainEmitter,
    ChatContext,
    make_event,
    encode_sse,
    StreamEventType,
)

async def custom_stream():
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    emitter = QueueDomainEmitter(queue=queue, loop=loop)
    
    context = ChatContext(
        conversation_id="conv_123",
        user_id="user_456",
        assistant_message_id="msg_789",
        emitter=emitter,
    )
    
    # 发送事件
    await emitter.aemit("meta.start", {
        "assistant_message_id": "msg_789",
    })
    await emitter.aemit("assistant.delta", {"delta": "你好"})
    await emitter.aemit("assistant.final", {"content": "你好"})
    await emitter.aemit("__end__", None)
    
    # 消费事件
    while True:
        evt = await queue.get()
        if evt["type"] == "__end__":
            break
        event = make_event(
            seq=1,
            conversation_id="conv_123",
            type=evt["type"],
            payload=evt["payload"],
        )
        print(encode_sse(event))
```

---

## 事件类型参考

### 流级别事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `meta.start` | `{ user_message_id, assistant_message_id }` | 流开始 |
| `assistant.final` | `{ content, reasoning?, products? }` | 流结束 |
| `error` | `{ message, code?, detail? }` | 错误 |

### LLM 调用事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `llm.call.start` | `{ message_count }` | LLM 调用开始 |
| `llm.call.end` | `{ elapsed_ms }` | LLM 调用结束 |
| `assistant.delta` | `{ delta }` | 文本增量 |
| `assistant.reasoning.delta` | `{ delta }` | 推理增量 |

### 工具调用事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `tool.start` | `{ tool_call_id, name, input? }` | 工具开始 |
| `tool.end` | `{ tool_call_id, name, status, output_preview?, error? }` | 工具结束 |

### 数据事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `assistant.products` | `{ items: [...] }` | 商品数据 |
| `assistant.todos` | `{ todos: [...] }` | TODO 列表 |
| `context.summarized` | `{ messages_before, messages_after }` | 上下文压缩 |

### 记忆事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `memory.extraction.start` | `{ conversation_id, user_id }` | 记忆抽取开始 |
| `memory.extraction.complete` | `{ facts_added, duration_ms }` | 记忆抽取完成 |
| `memory.profile.updated` | `{ user_id, updated_fields }` | 用户画像更新 |

### Supervisor 事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `agent.routed` | `{ source_agent, target_agent }` | Agent 路由 |
| `agent.handoff` | `{ from_agent, to_agent }` | Agent 切换 |
| `agent.complete` | `{ agent_id, elapsed_ms }` | 子 Agent 完成 |

### 中间件事件

| 事件类型 | Payload | 说明 |
|----------|---------|------|
| `model.retry.start` | `{ attempt, max_retries }` | 模型重试开始 |
| `model.fallback` | `{ from_model, to_model }` | 模型降级 |

---

## 许可证

MIT License
