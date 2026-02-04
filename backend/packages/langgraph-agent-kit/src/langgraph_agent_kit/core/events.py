"""聊天流事件类型定义

对外推送的事件类型（SSE 协议）。
事件类型建议集中定义，避免散落字符串。
"""

from __future__ import annotations

from enum import StrEnum


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
