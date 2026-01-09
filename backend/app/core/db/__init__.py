"""数据库抽象层

支持多种数据库后端（SQLite、PostgreSQL）的统一接口

模块组成：
- provider: SQLAlchemy 数据库 Provider（主数据库、爬虫数据库）
- checkpointer: LangGraph Checkpoint 工厂
- store: LangGraph Store 工厂
"""

from app.core.db.checkpointer import close_checkpointer, get_checkpointer
from app.core.db.provider import (
    DatabaseProvider,
    PostgresProvider,
    SQLiteProvider,
    close_database_provider,
    get_database_provider,
)
from app.core.db.store import close_store, get_store

__all__ = [
    # Provider
    "DatabaseProvider",
    "SQLiteProvider",
    "PostgresProvider",
    "get_database_provider",
    "close_database_provider",
    # Checkpointer
    "get_checkpointer",
    "close_checkpointer",
    # Store
    "get_store",
    "close_store",
]
