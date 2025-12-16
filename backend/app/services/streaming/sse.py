"""SSE 传输适配层（将 StreamEvent 序列化为 SSE frame）"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.schemas.stream import StreamEvent


def new_event_id() -> str:
    return f"evt_{uuid.uuid4()}"


def now_ms() -> int:
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


def encode_sse(event: StreamEvent) -> str:
    """将 StreamEvent 编码为 SSE 数据帧（只使用 data: 行）。"""

    # FastAPI/Starlette 会按字符串直接写出，这里保证每条事件以空行分隔
    data = event.model_dump()
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
