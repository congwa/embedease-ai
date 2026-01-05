"""WebSocket 心跳管理

职责：
- 定期检测连接活性
- 清理超时连接
"""

import asyncio
import time

from app.core.logging import get_logger

logger = get_logger("websocket.heartbeat")


class HeartbeatManager:
    """心跳管理器（单例）"""

    _instance: "HeartbeatManager | None" = None
    _task: asyncio.Task | None = None

    # 配置
    CHECK_INTERVAL = 30  # 检查间隔（秒）
    TIMEOUT = 90  # 超时时间（秒）

    def __new__(cls) -> "HeartbeatManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._task = None
        return cls._instance

    async def start(self) -> None:
        """启动心跳检测"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._check_loop())
            logger.info("WebSocket 心跳检测已启动")

    async def stop(self) -> None:
        """停止心跳检测"""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("WebSocket 心跳检测已停止")

    async def _check_loop(self) -> None:
        """心跳检测循环"""
        while True:
            try:
                await asyncio.sleep(self.CHECK_INTERVAL)
                await self._check_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("心跳检测出错", error=str(e))

    async def _check_connections(self) -> None:
        """检测所有连接"""
        from app.services.websocket.manager import ws_manager

        now = time.time()
        dead_conns = []

        all_conns = ws_manager.get_all_connections()
        for conn_id, conn in all_conns.items():
            if now - conn.last_ping_at > self.TIMEOUT:
                dead_conns.append(conn)

        for conn in dead_conns:
            logger.warning("连接超时，强制断开", conn_id=conn.id)
            await conn.close(code=4002, reason="心跳超时")
            await ws_manager.disconnect(conn.id)

        if dead_conns:
            logger.info(f"清理了 {len(dead_conns)} 个超时连接")


heartbeat_manager = HeartbeatManager()
