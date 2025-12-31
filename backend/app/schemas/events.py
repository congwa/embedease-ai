"""聊天流事件类型与 payload 类型定义（集中管理，便于扩展）。

约定：
- **domain event**：内部事件（工具/中间件/Agent 产出），结构为 `{ "type": str, "payload": Any }`
- **stream event**：对外协议事件（SSE 推送），结构为 `StreamEvent`（见 `app.schemas.stream`）

扩展方式：
1) 新增一个 `StreamEventType` 枚举成员（例如 `TOOL_PROGRESS = "tool.progress"`）
2) 如需强类型，增加对应的 payload TypedDict
3) 在 orchestrator / 前端 reducer 里按 type 处理即可
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, NotRequired, TypedDict


class NonLLMCallDomainEventType(StrEnum):
    """LLM 调用相邻 / 跨调用的内部事件分类。"""

    META_START = "meta.start" # 流开始，提供message_id对齐前端渲染/落库
    ASSISTANT_FINAL = "assistant.final" # 最终态（流结束前必出）

    LLM_CALL_START = "llm.call.start" # LLM调用开始
    # ... LLMCallDomainEventType 所有事件在中间触发
    LLM_CALL_END = "llm.call.end" # LLM调用结束

    MEMORY_EXTRACTION_START = "memory.extraction.start" # 记忆抽取开始
    MEMORY_EXTRACTION_COMPLETE = "memory.extraction.complete" # 记忆抽取完成
    MEMORY_PROFILE_UPDATED = "memory.profile.updated" # 用户画像更新

    # ========== 客服支持事件 ==========
    SUPPORT_HANDOFF_STARTED = "support.handoff_started"  # 客服介入开始
    SUPPORT_HANDOFF_ENDED = "support.handoff_ended"  # 客服介入结束
    SUPPORT_HUMAN_MESSAGE = "support.human_message"  # 人工客服消息
    SUPPORT_CONNECTED = "support.connected"  # 客服连接建立
    SUPPORT_PING = "support.ping"  # 心跳

    ERROR = "error"


class LLMCallDomainEventType(StrEnum):
    """单次 LLM 调用内部细粒度事件分类。"""

    ASSISTANT_REASONING_DELTA = "assistant.reasoning.delta" # 推理内容增量
    ASSISTANT_DELTA = "assistant.delta" # 文本增量
    ASSISTANT_PRODUCTS = "assistant.products" # 商品数据（仅在该调用内产生的）
    TOOL_START = "tool.start" # 工具开始
    TOOL_END = "tool.end" # 工具结束
    CONTEXT_SUMMARIZED = "context.summarized" # 上下文压缩完成
    ASSISTANT_TODOS = "assistant.todos" # TODO 规划列表更新（可能来自工具）


class StreamEventType(StrEnum):
    """对外推送的事件类型（SSE 协议），由领域事件枚举组成。"""

    # ========== 非 LLM 内部事件 ==========
    META_START = NonLLMCallDomainEventType.META_START.value
    ASSISTANT_FINAL = NonLLMCallDomainEventType.ASSISTANT_FINAL.value
    LLM_CALL_START = NonLLMCallDomainEventType.LLM_CALL_START.value
    LLM_CALL_END = NonLLMCallDomainEventType.LLM_CALL_END.value
    MEMORY_EXTRACTION_START = NonLLMCallDomainEventType.MEMORY_EXTRACTION_START.value
    MEMORY_EXTRACTION_COMPLETE = NonLLMCallDomainEventType.MEMORY_EXTRACTION_COMPLETE.value
    MEMORY_PROFILE_UPDATED = NonLLMCallDomainEventType.MEMORY_PROFILE_UPDATED.value
    SUPPORT_HANDOFF_STARTED = NonLLMCallDomainEventType.SUPPORT_HANDOFF_STARTED.value
    SUPPORT_HANDOFF_ENDED = NonLLMCallDomainEventType.SUPPORT_HANDOFF_ENDED.value
    SUPPORT_HUMAN_MESSAGE = NonLLMCallDomainEventType.SUPPORT_HUMAN_MESSAGE.value
    SUPPORT_CONNECTED = NonLLMCallDomainEventType.SUPPORT_CONNECTED.value
    SUPPORT_PING = NonLLMCallDomainEventType.SUPPORT_PING.value
    ERROR = NonLLMCallDomainEventType.ERROR.value

    # ========== LLM 调用内部事件 ==========
    ASSISTANT_REASONING_DELTA = LLMCallDomainEventType.ASSISTANT_REASONING_DELTA.value
    ASSISTANT_DELTA = LLMCallDomainEventType.ASSISTANT_DELTA.value
    ASSISTANT_PRODUCTS = LLMCallDomainEventType.ASSISTANT_PRODUCTS.value
    TOOL_START = LLMCallDomainEventType.TOOL_START.value
    TOOL_END = LLMCallDomainEventType.TOOL_END.value
    CONTEXT_SUMMARIZED = LLMCallDomainEventType.CONTEXT_SUMMARIZED.value
    ASSISTANT_TODOS = LLMCallDomainEventType.ASSISTANT_TODOS.value


class MetaStartPayload(TypedDict):
    user_message_id: str
    assistant_message_id: str


class TextDeltaPayload(TypedDict):
    delta: str


class ToolStartPayload(TypedDict):
    tool_call_id: str
    name: str
    input: NotRequired[Any]


class ToolEndPayload(TypedDict):
    tool_call_id: str
    name: str
    status: NotRequired[str]  # "success" | "error" | "empty"
    count: NotRequired[int]
    output_preview: NotRequired[Any]
    error: NotRequired[str]


class LlmCallStartPayload(TypedDict):
    message_count: int
    llm_call_id: NotRequired[str]


class LlmCallEndPayload(TypedDict):
    elapsed_ms: int
    message_count: NotRequired[int]
    error: NotRequired[str]
    llm_call_id: NotRequired[str]


class ErrorPayload(TypedDict):
    message: str
    code: NotRequired[str]
    detail: NotRequired[Any]


class MemoryExtractionStartPayload(TypedDict):
    conversation_id: str
    user_id: str


class MemoryExtractionCompletePayload(TypedDict):
    conversation_id: str
    user_id: str
    facts_added: NotRequired[int]
    entities_created: NotRequired[int]
    relations_created: NotRequired[int]
    duration_ms: NotRequired[int]
    status: NotRequired[str]  # "success" | "failed"
    error: NotRequired[str]


class MemoryProfileUpdatedPayload(TypedDict):
    user_id: str
    updated_fields: list[str]
    source: NotRequired[str]  # "fact" | "graph" | "user_input" | "system"


class TodoItem(TypedDict):
    """单个 TODO 项"""
    content: str
    status: str  # "pending" | "in_progress" | "completed"


class TodosPayload(TypedDict):
    """TODO 列表更新事件 payload"""
    todos: list[TodoItem]


class ContextSummarizedPayload(TypedDict):
    """上下文压缩完成事件 payload"""
    messages_before: int  # 压缩前消息数
    messages_after: int  # 压缩后消息数
    tokens_before: NotRequired[int]  # 压缩前 token 数（可选）
    tokens_after: NotRequired[int]  # 压缩后 token 数（可选）
