"""LangGraph Checkpointer 工厂

直接使用 LangGraph 官方提供的 AsyncSqliteSaver 和 AsyncPostgresSaver
"""

import asyncio
from typing import TYPE_CHECKING

import aiosqlite
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = get_logger("db.checkpointer")


class CheckpointerManager:
    """Checkpointer 管理器

    统一管理 SQLite 和 PostgreSQL 的 Checkpointer 实例
    """

    _instance: "CheckpointerManager | None" = None
    _checkpointer: BaseCheckpointSaver | None = None
    _conn: aiosqlite.Connection | None = None  # SQLite 连接
    _pool = None  # PostgreSQL 连接池
    _lock: asyncio.Lock

    def __new__(cls) -> "CheckpointerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def get_checkpointer(self) -> BaseCheckpointSaver:
        """获取 Checkpointer 实例"""
        async with self._lock:
            if self._checkpointer is not None:
                return self._checkpointer

            backend = settings.DATABASE_BACKEND

            if backend == "sqlite":
                self._checkpointer = await self._create_sqlite_checkpointer()
            elif backend == "postgres":
                self._checkpointer = await self._create_postgres_checkpointer()
            else:
                msg = f"不支持的数据库后端: {backend}"
                raise ValueError(msg)

            logger.info("Checkpointer 初始化完成", backend=backend)
            return self._checkpointer

    async def _create_sqlite_checkpointer(self) -> "AsyncSqliteSaver":
        """创建 SQLite Checkpointer"""
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        settings.ensure_data_dir()
        self._conn = await aiosqlite.connect(
            settings.CHECKPOINT_DB_PATH,
            isolation_level=None,
        )

        # 添加 is_alive 方法（兼容性）
        if not hasattr(self._conn, "is_alive"):
            import types

            def is_alive(conn) -> bool:  # noqa: ARG001
                return True

            self._conn.is_alive = types.MethodType(is_alive, self._conn)

        checkpointer = AsyncSqliteSaver(self._conn)
        await checkpointer.setup()
        return checkpointer

    async def _create_postgres_checkpointer(self) -> "AsyncPostgresSaver":
        """创建 PostgreSQL Checkpointer"""
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        conn_string = settings.checkpoint_connection_string

        # 使用连接池
        self._pool = AsyncConnectionPool(
            conninfo=conn_string,
            min_size=1,
            max_size=settings.DATABASE_POOL_SIZE,
            open=False,
        )
        await self._pool.open()

        checkpointer = AsyncPostgresSaver(self._pool)
        await checkpointer.setup()
        return checkpointer

    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            try:
                await self._conn.close()
            except Exception:
                pass
            self._conn = None

        if self._pool:
            try:
                await self._pool.close()
            except Exception:
                pass
            self._pool = None

        self._checkpointer = None
        logger.info("Checkpointer 连接已关闭")


# 单例管理器
_manager: CheckpointerManager | None = None


def _get_manager() -> CheckpointerManager:
    """获取 CheckpointerManager 单例"""
    global _manager
    if _manager is None:
        _manager = CheckpointerManager()
    return _manager


async def get_checkpointer() -> BaseCheckpointSaver:
    """获取 Checkpointer 实例"""
    return await _get_manager().get_checkpointer()


async def close_checkpointer() -> None:
    """关闭 Checkpointer 连接"""
    await _get_manager().close()
