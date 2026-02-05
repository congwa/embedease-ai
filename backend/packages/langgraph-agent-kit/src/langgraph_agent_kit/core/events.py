"""聊天流事件类型定义

对外推送的事件类型（SSE 协议）。
事件类型建议集中定义，避免散落字符串。
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, NotRequired, TypedDict


class StreamEventType(StrEnum):
    """对外推送的事件类型（SSE 协议）
    
    事件流顺序：
    1. meta.start - 流开始
    2. [循环] llm.call.start → [reasoning.delta, delta...] → llm.call.end
              → tool.start → [products, todos...] → tool.end
    3. memory.* - 后处理
    4. assistant.final - 流结束
    """

    # ========== 流级别事件 ==========
    META_START = "meta.start"
    ASSISTANT_FINAL = "assistant.final"
    ERROR = "error"

    # ========== LLM 调用边界 ==========
    LLM_CALL_START = "llm.call.start"
    LLM_CALL_END = "llm.call.end"

    # ========== LLM 调用内部增量 ==========
    ASSISTANT_REASONING_DELTA = "assistant.reasoning.delta"
    ASSISTANT_DELTA = "assistant.delta"

    # ========== 工具调用（在 llm.call.end 之后） ==========
    TOOL_START = "tool.start"
    TOOL_END = "tool.end"

    # ========== 数据事件 ==========
    ASSISTANT_PRODUCTS = "assistant.products"
    ASSISTANT_TODOS = "assistant.todos"
    CONTEXT_SUMMARIZED = "context.summarized"
    CONTEXT_TRIMMED = "context.trimmed"

    # ========== 后处理事件 ==========
    MEMORY_EXTRACTION_START = "memory.extraction.start"
    MEMORY_EXTRACTION_COMPLETE = "memory.extraction.complete"
    MEMORY_PROFILE_UPDATED = "memory.profile.updated"

    # ========== 客服支持事件 ==========
    SUPPORT_HANDOFF_STARTED = "support.handoff_started"
    SUPPORT_HANDOFF_ENDED = "support.handoff_ended"
    SUPPORT_HUMAN_MESSAGE = "support.human_message"
    SUPPORT_CONNECTED = "support.connected"
    SUPPORT_PING = "support.ping"

    # ========== Supervisor 多 Agent 编排事件 ==========
    AGENT_ROUTED = "agent.routed"
    AGENT_HANDOFF = "agent.handoff"
    AGENT_COMPLETE = "agent.complete"

    # ========== 技能事件 ==========
    SKILL_ACTIVATED = "skill.activated"
    SKILL_LOADED = "skill.loaded"

    # ========== 中间件事件 ==========
    MODEL_RETRY_START = "model.retry.start"
    MODEL_RETRY_FAILED = "model.retry.failed"
    MODEL_FALLBACK = "model.fallback"
    MODEL_CALL_LIMIT_EXCEEDED = "model.call_limit.exceeded"
    CONTEXT_EDITED = "context.edited"


# ==================== Payload TypedDict 定义 ====================


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
    messages_before: int
    messages_after: int
    tokens_before: NotRequired[int]
    tokens_after: NotRequired[int]


class ContextTrimmedPayload(TypedDict):
    """上下文滑动窗口裁剪事件 payload"""
    messages_before: int
    messages_after: int
    strategy: str  # "messages" | "tokens"


class AgentRoutedPayload(TypedDict):
    """Agent 路由事件 payload"""
    source_agent: str
    target_agent: str
    target_agent_name: str
    reason: NotRequired[str]


class AgentHandoffPayload(TypedDict):
    """Agent 切换事件 payload"""
    from_agent: str
    to_agent: str
    to_agent_name: str
    task: NotRequired[str]


class AgentCompletePayload(TypedDict):
    """子 Agent 任务完成事件 payload"""
    agent_id: str
    agent_name: str
    elapsed_ms: NotRequired[int]
    status: NotRequired[str]  # "success" | "error"


class SkillActivatedPayload(TypedDict):
    """技能激活事件 payload"""
    skill_id: str
    skill_name: str
    trigger_type: str  # "keyword" | "intent" | "manual"
    trigger_keyword: NotRequired[str]


class SkillLoadedPayload(TypedDict):
    """技能加载事件 payload"""
    skill_id: str
    skill_name: str
    skill_category: str


class ModelRetryStartPayload(TypedDict):
    """模型重试开始事件 payload"""
    attempt: int
    max_retries: int
    delay_ms: int
    error_type: str
    error_message: NotRequired[str]


class ModelRetryFailedPayload(TypedDict):
    """模型重试失败事件 payload"""
    total_attempts: int
    final_error: str
    on_failure: str  # "continue" | "error"


class ModelFallbackPayload(TypedDict):
    """模型降级事件 payload"""
    from_model: str
    to_model: str
    fallback_index: int
    total_fallbacks: int
    error_type: str
    error_message: NotRequired[str]


class ModelCallLimitExceededPayload(TypedDict):
    """模型调用限制超限事件 payload"""
    thread_count: NotRequired[int]
    run_count: NotRequired[int]
    thread_limit: NotRequired[int]
    run_limit: NotRequired[int]
    exceeded_type: str  # "thread" | "run" | "both"
    exit_behavior: str  # "end" | "error"


class ContextEditedPayload(TypedDict):
    """上下文编辑事件 payload"""
    strategy: str  # "clear_tool_uses"
    tokens_before: NotRequired[int]
    tokens_after: NotRequired[int]
    tools_cleared: int
    kept: int
