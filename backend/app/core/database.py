"""数据库连接管理

使用 Provider 模式支持多种数据库后端（SQLite、PostgreSQL）
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.provider import get_database_provider
from app.core.logging import get_logger

logger = get_logger("database")


def get_engine():
    """获取数据库引擎（兼容旧代码）"""
    return get_database_provider().engine


def get_session_factory():
    """获取会话工厂（兼容旧代码）"""
    return get_database_provider().session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    session_factory = get_database_provider().session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（上下文管理器）"""
    session_factory = get_database_provider().session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise


async def init_db() -> None:
    """初始化数据库（创建表）"""
    from app.core.config import settings
    from app.models.base import Base

    settings.ensure_data_dir()
    provider = get_database_provider()
    await provider.init_db(Base)
    logger.info(
        "数据库表初始化完成",
        backend=provider.backend_name,
    )
