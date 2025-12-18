"""LangGraph Context：在工具/中间件/节点内统一发出流式事件。

目标：让工具/中间件不关心 HTTP/SSE，只关心 `type + payload`。

用法：
- Orchestrator 在一次 chat run 开始时创建 `ChatContext(emitter=...)`
- 调用 agent 时通过 `context=ChatContext(...)` 注入
- 工具签名可接收 `ToolRuntime`，然后 `runtime.context.emitter.emit(...)`
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field, ConfigDict


class DomainEmitter(Protocol):
    """业务事件发射器（不关心 SSE/HTTP，只关心 type + payload）。"""

    def emit(self, type: str, payload: Any) -> None: ...


class ChatContext(BaseModel):
    """Graph run scoped context（通过 LangGraph 的 invoke/stream 传入 context 注入）。

    说明：
    - LangGraph 会把 context 注入到 Runtime.context
    - ToolNode 会把 Runtime.context 注入到 ToolRuntime.context
    - 因此 middleware/tools 都能通过 runtime.context 访问同一个 ChatContext
    """

    conversation_id: str
    user_id: str
    assistant_message_id: str
    mode: str = "natural"  # 聊天模式：natural / free / strict
    emitter: Any = Field(exclude=True, repr=False)  # 排除序列化，避免把 emitter/loop/queue 带进日志

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # 允许任意类型（用于 emitter）
        frozen=True,  # 保持不可变性，类似原来的 frozen=True
    )
