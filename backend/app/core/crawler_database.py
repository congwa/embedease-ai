"""爬虫数据库连接管理

独立的爬虫数据库，与主应用数据库分离，避免：
1. 爬虫长事务阻塞用户查询
2. 死锁风险
3. 数据库文件过大

写入 Product 时使用独立的短事务连接主数据库，快速写入后立即释放。

注意：PostgreSQL 模式下，爬虫数据使用同一数据库，通过表名区分。
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

logger = get_logger("crawler.database")

# ========== 爬虫数据库 Provider ==========
_crawler_engine: AsyncEngine | None = None
_crawler_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_crawler_engine() -> AsyncEngine:
    """获取爬虫数据库引擎"""
    global _crawler_engine
    if _crawler_engine is None:
        backend = settings.DATABASE_BACKEND
        if backend == "sqlite":
            _crawler_engine = create_async_engine(
                settings.crawler_database_url,
                connect_args={"timeout": 30, "check_same_thread": False},
                echo=False,
                future=True,
            )
        elif backend == "postgres":
            _crawler_engine = create_async_engine(
                settings.crawler_database_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                echo=False,
                future=True,
            )
        else:
            msg = f"不支持的数据库后端: {backend}"
            raise ValueError(msg)
        logger.info("爬虫数据库引擎初始化", backend=backend)
    return _crawler_engine


def _get_crawler_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取爬虫数据库会话工厂"""
    global _crawler_session_factory
    if _crawler_session_factory is None:
        _crawler_session_factory = async_sessionmaker(
            _get_crawler_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _crawler_session_factory


@asynccontextmanager
async def get_crawler_db() -> AsyncGenerator[AsyncSession, None]:
    """获取爬虫数据库会话（上下文管理器）

    用于爬虫相关的数据操作（CrawlSite, CrawlTask, CrawlPage）
    """
    session_factory = _get_crawler_session_factory()
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


async def get_crawler_db_dep() -> AsyncGenerator[AsyncSession, None]:
    """获取爬虫数据库会话（用于 FastAPI 依赖注入）

    用于爬虫相关的数据操作（CrawlSite, CrawlTask, CrawlPage）
    """
    session_factory = _get_crawler_session_factory()
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


async def init_crawler_db() -> None:
    """初始化爬虫数据库（创建表）"""
    from app.models.crawler import CrawlerBase

    settings.ensure_data_dir()
    engine = _get_crawler_engine()
    backend = settings.DATABASE_BACKEND

    async with engine.begin() as conn:
        if backend == "sqlite":
            await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.run_sync(CrawlerBase.metadata.create_all)

    logger.info("爬虫数据库表初始化完成", backend=backend)
