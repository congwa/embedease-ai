"""Handler 基类和工具函数"""

import time
from typing import Any
from uuid import uuid4

from app.schemas.websocket import WS_PROTOCOL_VERSION, WSAction


def build_server_message(
    action: str | WSAction,
    payload: dict[str, Any],
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """构建服务器推送消息"""
    return {
        "v": WS_PROTOCOL_VERSION,
        "id": str(uuid4()),
        "ts": int(time.time() * 1000),
        "action": action.value if isinstance(action, WSAction) else action,
        "payload": payload,
        "conversation_id": conversation_id,
    }
