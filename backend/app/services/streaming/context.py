"""LangGraph Context：在工具/中间件/节点内统一发出流式事件。

目标：让工具/中间件不关心 HTTP/SSE，只关心 `type + payload`。

用法：
- Orchestrator 在一次 chat run 开始时创建 `ChatContext(emitter=...)`
- 调用 agent 时通过 `context=ChatContext(...)` 注入
- 工具签名可接收 `ToolRuntime`，然后 `runtime.context.emitter.emit(...)`

注意：不使用 context_schema 以避免 Pydantic JsonSchema 生成问题
"""

from __future__ import annotations

from typing import Any, Protocol


class DomainEmitter(Protocol):
    """业务事件发射器（不关心 SSE/HTTP，只关心 type + payload）。"""

    def emit(self, type: str, payload: Any) -> None: ...


class ChatContext:
    """Graph run scoped context（通过 astream_events 的 context 参数注入）。

    使用简单的类而非 Pydantic BaseModel，避免 JsonSchema 生成问题。
    LangChain 会将此对象注入到 ToolRuntime.context 中。
    """

    def __init__(
        self,
        conversation_id: str,
        user_id: str,
        assistant_message_id: str,
        emitter: Any,
    ) -> None:
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.assistant_message_id = assistant_message_id
        self.emitter = emitter

    def __repr__(self) -> str:
        return (
            f"ChatContext(conversation_id={self.conversation_id!r}, "
            f"user_id={self.user_id!r}, "
            f"assistant_message_id={self.assistant_message_id!r})"
        )
