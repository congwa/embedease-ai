"""LangGraph Store 工厂

使用 LangGraph 官方的 AsyncSqliteStore 和 AsyncPostgresStore
"""

import asyncio
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langgraph.store.base import BaseStore

logger = get_logger("db.store")


class StoreManager:
    """Store 管理器

    统一管理 SQLite 和 PostgreSQL 的 Store 实例
    """

    _instance: "StoreManager | None" = None
    _store: "BaseStore | None" = None
    _lock: asyncio.Lock

    def __new__(cls) -> "StoreManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def get_store(self) -> "BaseStore":
        """获取 Store 实例"""
        async with self._lock:
            if self._store is not None:
                return self._store

            backend = settings.DATABASE_BACKEND

            if backend == "sqlite":
                self._store = await self._create_sqlite_store()
            elif backend == "postgres":
                self._store = await self._create_postgres_store()
            else:
                msg = f"不支持的数据库后端: {backend}"
                raise ValueError(msg)

            logger.info("Store 初始化完成", backend=backend)
            return self._store

    async def _create_sqlite_store(self) -> "BaseStore":
        """创建 SQLite Store"""
        from langgraph.store.sqlite.aio import AsyncSqliteStore

        settings.ensure_memory_dirs()

        # 使用上下文管理器创建 store
        store = await AsyncSqliteStore.from_conn_string(settings.MEMORY_STORE_DB_PATH).__aenter__()
        await store.setup()
        return store

    async def _create_postgres_store(self) -> "BaseStore":
        """创建 PostgreSQL Store"""
        from langgraph.store.postgres.aio import AsyncPostgresStore

        conn_string = settings.checkpoint_connection_string

        # 使用上下文管理器创建 store
        store = await AsyncPostgresStore.from_conn_string(conn_string).__aenter__()
        await store.setup()
        return store

    async def close(self) -> None:
        """关闭 Store"""
        self._store = None
        logger.info("Store 已关闭")


# 单例管理器
_manager: StoreManager | None = None


def _get_manager() -> StoreManager:
    """获取 StoreManager 单例"""
    global _manager
    if _manager is None:
        _manager = StoreManager()
    return _manager


async def get_store() -> "BaseStore":
    """获取 Store 实例"""
    return await _get_manager().get_store()


async def close_store() -> None:
    """关闭 Store"""
    await _get_manager().close()
