"""爬虫数据库连接管理

独立的爬虫数据库，与主应用数据库分离，避免：
1. 爬虫长事务阻塞用户查询
2. 死锁风险
3. 数据库文件过大

写入 Product 时使用独立的短事务连接主数据库，快速写入后立即释放。
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("crawler.database")

# 创建爬虫数据库引擎
crawler_engine = create_async_engine(
    settings.crawler_database_url,
    connect_args={"timeout": 30, "check_same_thread": False},
    echo=False,
    future=True,
)

# 创建爬虫数据库会话工厂
crawler_session_factory = async_sessionmaker(
    crawler_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_crawler_db() -> AsyncGenerator[AsyncSession, None]:
    """获取爬虫数据库会话（上下文管理器）
    
    用于爬虫相关的数据操作（CrawlSite, CrawlTask, CrawlPage）
    """
    async with crawler_session_factory() as session:
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
    async with crawler_session_factory() as session:
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
    async with crawler_engine.begin() as conn:
        # 先切到 WAL，允许并发读写
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        # 再创建表
        await conn.run_sync(CrawlerBase.metadata.create_all)
    logger.info("爬虫数据库表初始化完成", path=settings.CRAWLER_DATABASE_PATH)
