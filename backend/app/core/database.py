"""数据库连接管理

使用 Provider 模式支持多种数据库后端（SQLite、PostgreSQL）

SQLite 防死锁策略：
1. NullPool：每次请求创建新连接，避免多连接争抢写入锁
2. WAL 模式：允许读写并发
3. synchronous=NORMAL：在 WAL 模式下安全且高性能
4. busy_timeout=30s：等待锁释放而非立即失败
5. 写入串行化锁（可选）：通过 get_db_write_context() 强制写入串行化
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.provider import get_database_provider
from app.core.logging import get_logger

logger = get_logger("database")

# SQLite 写入串行化锁（仅在需要强制串行化写入时使用）
_write_lock = asyncio.Lock()


def get_engine():
    """获取数据库引擎（兼容旧代码）"""
    return get_database_provider().engine


def get_session_factory():
    """获取会话工厂（兼容旧代码）"""
    return get_database_provider().session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    session_factory = get_database_provider().session_factory
    start = time.perf_counter()
    logger.debug("get_db: 开始创建 session")
    async with session_factory() as session:
        logger.debug(f"get_db: session 已创建，耗时 {(time.perf_counter() - start) * 1000:.2f}ms")
        try:
            yield session
            commit_start = time.perf_counter()
            logger.debug("get_db: 开始 commit")
            await session.commit()
            logger.debug(f"get_db: commit 完成，耗时 {(time.perf_counter() - commit_start) * 1000:.2f}ms")
        except asyncio.CancelledError:
            logger.debug("get_db: 请求被取消，开始 rollback")
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            logger.debug(f"get_db: 发生异常 {type(e).__name__}，开始 rollback")
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            logger.debug(f"get_db: session 结束，总耗时 {(time.perf_counter() - start) * 1000:.2f}ms")


# 别名，兼容旧代码
get_session = get_db


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


@asynccontextmanager
async def get_db_write_context() -> AsyncGenerator[AsyncSession, None]:
    """获取写入专用数据库会话（串行化）
    
    通过 asyncio.Lock 确保同一时间只有一个写入事务在执行。
    适用于需要强制串行化写入的场景，如：
    - 批量导入数据
    - 关键业务写入（避免死锁）
    
    注意：由于使用了 NullPool + WAL，大多数场景下不需要使用此方法。
    仅在确实需要强制串行化时使用。
    
    示例：
        async with get_db_write_context() as session:
            await session.execute(insert_stmt)
    """
    async with _write_lock:
        async with get_db_context() as session:
            yield session


async def init_db() -> None:
    """初始化数据库（创建表 + 增量迁移）"""
    from app.core.config import settings
    from app.models.base import Base

    settings.ensure_data_dir()
    provider = get_database_provider()
    await provider.init_db(Base)
    await _migrate_schema(provider)
    logger.info(
        "数据库表初始化完成",
        backend=provider.backend_name,
    )


async def _migrate_schema(provider) -> None:
    """增量 schema 迁移：为已存在的表新增列。

    create_all 只创建不存在的表，不会修改已有表结构。
    此函数负责为已有表补充新增列，支持 SQLite 和 PostgreSQL。
    """
    from sqlalchemy import text

    # agents 表需要新增的客诉角色字段
    agents_new_columns: list[tuple[str, str]] = [
        ("role_tag", "VARCHAR(50)"),
        ("business_domain", "VARCHAR(100)"),
        ("skill_bundle_ids", "TEXT"),
        ("knowledge_scope", "VARCHAR(200)"),
        ("review_schema_name", "VARCHAR(100)"),
        ("handoff_rules", "TEXT"),
    ]

    engine = provider.engine
    backend = provider.backend_name

    try:
        async with engine.begin() as conn:
            if backend == "sqlite":
                result = await conn.execute(text("PRAGMA table_info(agents)"))
                existing_cols = {row[1] for row in result.fetchall()}
                for col_name, col_type in agents_new_columns:
                    if col_name not in existing_cols:
                        await conn.execute(
                            text(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")
                        )
                        logger.info("agents 表新增列", column=col_name)
            else:
                # PostgreSQL 支持 IF NOT EXISTS
                for col_name, col_type in agents_new_columns:
                    await conn.execute(
                        text(
                            f"ALTER TABLE agents ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    )
    except Exception as e:
        logger.warning("schema 迁移出现异常，可能列已存在", error=str(e))
