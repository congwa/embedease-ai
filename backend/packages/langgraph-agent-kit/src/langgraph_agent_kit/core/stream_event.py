"""流式事件协议（统一封装）"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StreamEvent(BaseModel):
    """统一的流式事件 Envelope。

    该结构用于解耦：
    - 业务事件生产（Agent/工具调用）
    - 传输层（SSE/WebSocket 等）
    - 前端渲染（基于 type + payload）

    ## 使用方式（后端）
    - **内部（domain）**：工具/中间件/Agent 产出 `{ "type": "...", "payload": {...} }`
    - **对外（stream）**：Orchestrator 将 domain event 封装为 StreamEvent 并通过 SSE 推送

    ## type/payload 约定
    事件类型建议集中定义在 `StreamEventType`，避免散落字符串：
    - `meta.start`：开流第一条，提供 assistant_message_id，用于前端对齐渲染与落库
    - `assistant.delta`：文本增量
    - `assistant.products`：商品列表
    - `assistant.final`：最终态（流结束前必出）
    - `tool.*` / `llm.call.*`：过程事件（可选）
    - `error`：错误事件
    """

    v: int = Field(default=1, description="协议版本")
    id: str = Field(..., description="事件 ID")
    seq: int = Field(..., description="同一条流内的递增序号，从 1 开始")
    ts: int = Field(..., description="事件产生时间戳（毫秒）")

    conversation_id: str = Field(..., description="会话 ID")
    message_id: str | None = Field(None, description="助手消息 ID（用于前端对齐/落库）")

    type: str = Field(
        ..., description="事件类型（命名空间：meta.* / assistant.* / tool.* / error）"
    )
    payload: Any = Field(default_factory=dict, description="事件载荷（按 type 变化）")
