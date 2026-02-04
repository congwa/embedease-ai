"""SSE 传输适配层（将 StreamEvent 序列化为 SSE frame）"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from langgraph_agent_kit.core.stream_event import StreamEvent


def new_event_id() -> str:
    """生成唯一事件 ID"""
    return f"evt_{uuid.uuid4()}"


def now_ms() -> int:
    """获取当前毫秒时间戳"""
    return int(time.time() * 1000)


def make_event(
    *,
    seq: int,
    conversation_id: str,
    type: str,
    payload: Any,
    message_id: str | None = None,
    event_id: str | None = None,
    ts: int | None = None,
    v: int = 1,
) -> StreamEvent:
    """创建 StreamEvent 实例"""
    return StreamEvent(
        v=v,
        id=event_id or new_event_id(),
        seq=seq,
        ts=ts or now_ms(),
        conversation_id=conversation_id,
        message_id=message_id,
        type=type,
        payload=payload,
    )


def encode_sse(event: StreamEvent | dict[str, Any]) -> str:
    """将 StreamEvent 编码为 SSE 数据帧（只使用 data: 行）。
    
    支持传入 StreamEvent 模型或普通字典。
    """
    if isinstance(event, dict):
        data = event
    else:
        data = event.model_dump()
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
