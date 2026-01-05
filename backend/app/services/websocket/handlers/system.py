"""系统消息处理器"""

import time
from typing import Any

from app.core.logging import get_logger
from app.schemas.websocket import WSAction
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import WSConnection
from app.services.websocket.router import ws_router

logger = get_logger("websocket.handlers.system")


@ws_router.handler(WSAction.SYSTEM_PING)
async def handle_ping(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理心跳"""
    conn.last_ping_at = time.time()

    pong_msg = build_server_message(
        action=WSAction.SYSTEM_PONG,
        payload={"server_ts": int(time.time() * 1000)},
    )
    await conn.send(pong_msg)
