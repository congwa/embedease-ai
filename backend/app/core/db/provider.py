"""数据库 Provider 抽象层

支持 SQLite 和 PostgreSQL 的统一数据库提供者接口
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

from app.core.logging import get_logger

logger = get_logger("db.provider")


class DatabaseProvider(ABC):
    """数据库提供者抽象基类"""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """返回后端名称: sqlite, postgres"""

    @property
    @abstractmethod
    def engine(self) -> AsyncEngine:
        """获取 SQLAlchemy 异步引擎"""

    @property
    @abstractmethod
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """获取会话工厂"""

    @abstractmethod
    async def init_db(self, base: "type[DeclarativeBase]") -> None:
        """初始化数据库（创建表）"""

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""


class SQLiteProvider(DatabaseProvider):
    """SQLite 数据库提供者"""

    def __init__(self, database_url: str):
        self._database_url = database_url
        self._engine = create_async_engine(
            database_url,
            connect_args={"timeout": 30, "check_same_thread": False},
            echo=False,
            future=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    @property
    def backend_name(self) -> str:
        return "sqlite"

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def init_db(self, base: "type[DeclarativeBase]") -> None:
        async with self._engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.run_sync(base.metadata.create_all)
        logger.info("SQLite 数据库初始化完成")

    async def close(self) -> None:
        await self._engine.dispose()
        logger.info("SQLite 连接已关闭")


class PostgresProvider(DatabaseProvider):
    """PostgreSQL 数据库提供者"""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
    ):
        self._database_url = database_url
        self._pool_size = pool_size
        self._engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            echo=False,
            future=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    @property
    def backend_name(self) -> str:
        return "postgres"

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @property
    def pool_size(self) -> int:
        return self._pool_size

    async def init_db(self, base: "type[DeclarativeBase]") -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)
        logger.info("PostgreSQL 数据库初始化完成")

    async def close(self) -> None:
        await self._engine.dispose()
        logger.info("PostgreSQL 连接已关闭")


# ========== 单例管理 ==========
_provider: DatabaseProvider | None = None


def get_database_provider() -> DatabaseProvider:
    """获取数据库提供者（单例）

    根据 DATABASE_BACKEND 配置自动选择 SQLite 或 PostgreSQL
    """
    global _provider
    if _provider is None:
        from app.core.config import settings

        backend = settings.DATABASE_BACKEND
        if backend == "sqlite":
            _provider = SQLiteProvider(settings.database_url)
            logger.info("数据库 Provider 初始化", backend="sqlite", path=settings.DATABASE_PATH)
        elif backend == "postgres":
            _provider = PostgresProvider(
                settings.database_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            )
            logger.info(
                "数据库 Provider 初始化",
                backend="postgres",
                host=settings.POSTGRES_HOST,
                pool_size=settings.DATABASE_POOL_SIZE,
            )
        else:
            msg = f"不支持的数据库后端: {backend}"
            raise ValueError(msg)
    return _provider


async def close_database_provider() -> None:
    """关闭数据库提供者"""
    global _provider
    if _provider is not None:
        await _provider.close()
        _provider = None
