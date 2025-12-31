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


class StreamLevelEventType(StrEnum):
    """流级别事件：贯穿整个 SSE 流的生命周期。"""

    META_START = "meta.start"  # 流开始，提供 message_id 对齐前端渲染/落库
    ASSISTANT_FINAL = "assistant.final"  # 最终态（流结束前必出）
    ERROR = "error"  # 错误事件


class LLMCallBoundaryEventType(StrEnum):
    """LLM 调用边界事件：标记单次 LLM 调用的开始和结束。"""

    LLM_CALL_START = "llm.call.start"  # LLM 调用开始
    LLM_CALL_END = "llm.call.end"  # LLM 调用结束


class LLMCallInternalEventType(StrEnum):
    """LLM 调用内部事件：仅在 llm.call.start → llm.call.end 之间触发。"""

    ASSISTANT_REASONING_DELTA = "assistant.reasoning.delta"  # 推理内容增量
    ASSISTANT_DELTA = "assistant.delta"  # 文本增量


class ToolCallEventType(StrEnum):
    """工具调用事件：在 llm.call.end 之后触发，独立于 LLM 调用。
    
    真实事件流：
    llm.call.start → [reasoning.delta, delta...] → llm.call.end
    → tool.start → [中间推送] → tool.end
    → llm.call.start → [...] → llm.call.end (下一轮)
    """

    TOOL_START = "tool.start"  # 工具开始
    TOOL_END = "tool.end"  # 工具结束


class DataEventType(StrEnum):
    """数据事件：可能在 LLM 调用内部或工具执行时产生。"""

    ASSISTANT_PRODUCTS = "assistant.products"  # 商品数据
    ASSISTANT_TODOS = "assistant.todos"  # TODO 规划列表更新
    CONTEXT_SUMMARIZED = "context.summarized"  # 上下文压缩完成


class PostProcessEventType(StrEnum):
    """后处理事件：流末尾的后处理操作。"""

    MEMORY_EXTRACTION_START = "memory.extraction.start"  # 记忆抽取开始
    MEMORY_EXTRACTION_COMPLETE = "memory.extraction.complete"  # 记忆抽取完成
    MEMORY_PROFILE_UPDATED = "memory.profile.updated"  # 用户画像更新


class SupportEventType(StrEnum):
    """客服支持事件。"""

    SUPPORT_HANDOFF_STARTED = "support.handoff_started"  # 客服介入开始
    SUPPORT_HANDOFF_ENDED = "support.handoff_ended"  # 客服介入结束
    SUPPORT_HUMAN_MESSAGE = "support.human_message"  # 人工客服消息
    SUPPORT_CONNECTED = "support.connected"  # 客服连接建立
    SUPPORT_PING = "support.ping"  # 心跳


# ==================== 兼容旧代码的别名 ====================

class NonLLMCallDomainEventType(StrEnum):
    """[已废弃] 请使用更细粒度的事件类型枚举。"""

    META_START = StreamLevelEventType.META_START.value
    ASSISTANT_FINAL = StreamLevelEventType.ASSISTANT_FINAL.value
    LLM_CALL_START = LLMCallBoundaryEventType.LLM_CALL_START.value
    LLM_CALL_END = LLMCallBoundaryEventType.LLM_CALL_END.value
    MEMORY_EXTRACTION_START = PostProcessEventType.MEMORY_EXTRACTION_START.value
    MEMORY_EXTRACTION_COMPLETE = PostProcessEventType.MEMORY_EXTRACTION_COMPLETE.value
    MEMORY_PROFILE_UPDATED = PostProcessEventType.MEMORY_PROFILE_UPDATED.value
    SUPPORT_HANDOFF_STARTED = SupportEventType.SUPPORT_HANDOFF_STARTED.value
    SUPPORT_HANDOFF_ENDED = SupportEventType.SUPPORT_HANDOFF_ENDED.value
    SUPPORT_HUMAN_MESSAGE = SupportEventType.SUPPORT_HUMAN_MESSAGE.value
    SUPPORT_CONNECTED = SupportEventType.SUPPORT_CONNECTED.value
    SUPPORT_PING = SupportEventType.SUPPORT_PING.value
    ERROR = StreamLevelEventType.ERROR.value


class LLMCallDomainEventType(StrEnum):
    """[已废弃] 请使用更细粒度的事件类型枚举。
    
    注意：tool.start/tool.end 已移至 ToolCallEventType，
    因为它们实际发生在 llm.call.end 之后，不属于 LLM 调用内部。
    """

    ASSISTANT_REASONING_DELTA = LLMCallInternalEventType.ASSISTANT_REASONING_DELTA.value
    ASSISTANT_DELTA = LLMCallInternalEventType.ASSISTANT_DELTA.value
    ASSISTANT_PRODUCTS = DataEventType.ASSISTANT_PRODUCTS.value
    TOOL_START = ToolCallEventType.TOOL_START.value
    TOOL_END = ToolCallEventType.TOOL_END.value
    CONTEXT_SUMMARIZED = DataEventType.CONTEXT_SUMMARIZED.value
    ASSISTANT_TODOS = DataEventType.ASSISTANT_TODOS.value


class StreamEventType(StrEnum):
    """对外推送的事件类型（SSE 协议）。
    
    事件流顺序：
    1. meta.start - 流开始
    2. [循环] llm.call.start → [reasoning.delta, delta...] → llm.call.end
              → tool.start → [products, todos...] → tool.end
    3. memory.* - 后处理
    4. assistant.final - 流结束
    """

    # ========== 流级别事件 ==========
    META_START = StreamLevelEventType.META_START.value
    ASSISTANT_FINAL = StreamLevelEventType.ASSISTANT_FINAL.value
    ERROR = StreamLevelEventType.ERROR.value

    # ========== LLM 调用边界 ==========
    LLM_CALL_START = LLMCallBoundaryEventType.LLM_CALL_START.value
    LLM_CALL_END = LLMCallBoundaryEventType.LLM_CALL_END.value

    # ========== LLM 调用内部增量 ==========
    ASSISTANT_REASONING_DELTA = LLMCallInternalEventType.ASSISTANT_REASONING_DELTA.value
    ASSISTANT_DELTA = LLMCallInternalEventType.ASSISTANT_DELTA.value

    # ========== 工具调用（在 llm.call.end 之后） ==========
    TOOL_START = ToolCallEventType.TOOL_START.value
    TOOL_END = ToolCallEventType.TOOL_END.value

    # ========== 数据事件 ==========
    ASSISTANT_PRODUCTS = DataEventType.ASSISTANT_PRODUCTS.value
    ASSISTANT_TODOS = DataEventType.ASSISTANT_TODOS.value
    CONTEXT_SUMMARIZED = DataEventType.CONTEXT_SUMMARIZED.value

    # ========== 后处理事件 ==========
    MEMORY_EXTRACTION_START = PostProcessEventType.MEMORY_EXTRACTION_START.value
    MEMORY_EXTRACTION_COMPLETE = PostProcessEventType.MEMORY_EXTRACTION_COMPLETE.value
    MEMORY_PROFILE_UPDATED = PostProcessEventType.MEMORY_PROFILE_UPDATED.value

    # ========== 客服支持事件 ==========
    SUPPORT_HANDOFF_STARTED = SupportEventType.SUPPORT_HANDOFF_STARTED.value
    SUPPORT_HANDOFF_ENDED = SupportEventType.SUPPORT_HANDOFF_ENDED.value
    SUPPORT_HUMAN_MESSAGE = SupportEventType.SUPPORT_HUMAN_MESSAGE.value
    SUPPORT_CONNECTED = SupportEventType.SUPPORT_CONNECTED.value
    SUPPORT_PING = SupportEventType.SUPPORT_PING.value


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
