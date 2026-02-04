"""LangGraph Context：在工具/中间件/节点内统一发出流式事件。

目标：让工具/中间件不关心 HTTP/SSE，只关心 `type + payload`。

用法：
- Orchestrator 在一次 chat run 开始时创建 `ChatContext(emitter=...)`
- 调用 agent 时通过 `context=ChatContext(...)` 注入
- 工具签名可接收 `ToolRuntime`，然后 `runtime.context.emitter.emit(...)`

数据库会话：
- 路由层通过 `db=session` 传入数据库会话
- 工具可通过 `runtime.context.db` 获取会话（避免在工具内部创建新会话）
- 如果 db 为 None，工具应使用数据库上下文管理器创建临时会话
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class DomainEmitter(Protocol):
    """业务事件发射器协议（不关心 SSE/HTTP，只关心 type + payload）。"""

    def emit(self, type: str, payload: Any) -> None:
        """同步发射事件"""
        ...

    async def aemit(self, type: str, payload: Any) -> None:
        """异步发射事件"""
        ...


class ChatContext(BaseModel):
    """Graph run scoped context（通过 LangGraph 的 invoke/stream 传入 context 注入）。

    说明：
    - LangGraph 会把 context 注入到 Runtime.context
    - ToolNode 会把 Runtime.context 注入到 ToolRuntime.context
    - 因此 middleware/tools 都能通过 runtime.context 访问同一个 ChatContext

    数据库会话：
    - db: 可选的数据库会话，由路由层注入
    - 工具优先使用 context.db，若为 None 则创建临时会话
    """

    conversation_id: str
    user_id: str
    assistant_message_id: str
    emitter: Any = Field(exclude=True, repr=False)
    db: Any = Field(default=None, exclude=True, repr=False)
    response_latency_ms: int | None = None

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def get_db_session(self) -> Any | None:
        """获取数据库会话（类型安全的访问方式）"""
        return self.db
