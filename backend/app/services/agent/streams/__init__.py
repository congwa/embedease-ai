"""流处理模块

本模块包含 Agent 流响应的解析和事件发射逻辑。
使用 SDK 的 StreamingResponseHandler，并提供业务扩展版本。
"""

from langgraph_agent_kit import StreamingResponseHandler

from app.services.agent.streams.business_handler import (
    BusinessResponseHandler,
    normalize_products_payload,
)

__all__ = [
    "StreamingResponseHandler",
    "BusinessResponseHandler",
    "normalize_products_payload",
]
