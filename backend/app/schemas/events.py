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


class StreamEventType(StrEnum):
    """对外推送的事件类型（SSE 协议）。"""

    META_START = "meta.start"

    ASSISTANT_DELTA = "assistant.delta"
    ASSISTANT_REASONING_DELTA = "assistant.reasoning.delta"
    ASSISTANT_PRODUCTS = "assistant.products"
    ASSISTANT_FINAL = "assistant.final"

    TOOL_START = "tool.start"
    TOOL_END = "tool.end"

    LLM_CALL_START = "llm.call.start"
    LLM_CALL_END = "llm.call.end"

    ERROR = "error"


class MetaStartPayload(TypedDict):
    user_message_id: str
    assistant_message_id: str


class TextDeltaPayload(TypedDict):
    delta: str


class ToolStartPayload(TypedDict):
    name: str
    input: NotRequired[Any]


class ToolEndPayload(TypedDict):
    name: str
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
