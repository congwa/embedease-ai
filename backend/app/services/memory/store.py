"""LangGraph Store 长期记忆基座

实现 langgraph.store.base.BaseStore 接口，作为跨会话的全局偏好/状态仓库。
支持用户画像、任务进度、功能开关等跨对话共享信息。

支持多种数据库后端：SQLite（默认）、PostgreSQL
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("memory.store")


class Item:
    """Store 条目"""

    def __init__(
        self,
        namespace: tuple[str, ...],
        key: str,
        value: dict[str, Any],
        created_at: datetime,
        updated_at: datetime,
    ):
        self.namespace = namespace
        self.key = key
        self.value = value
        self.created_at = created_at
        self.updated_at = updated_at

    def __repr__(self) -> str:
        return f"Item(namespace={self.namespace}, key={self.key})"


class UserProfileStore:
    """用户画像 Store

    支持多种数据库后端：SQLite（默认）、PostgreSQL
    - namespace: ("users", user_id) 格式隔离
    - 跨会话共享用户偏好、任务进度等

    用法：
    ```python
    store = await get_user_profile_store()

    # 获取用户画像
    profile = await store.get_user_profile("user_123")

    # 设置用户画像
    await store.set_user_profile("user_123", {
        "nickname": "小明",
        "budget_range": [1000, 5000],
        "favorite_categories": ["手机", "电脑"],
    })

    # 通用 put/get
    await store.put(("users", "user_123"), "preferences", {"theme": "dark"})
    item = await store.get(("users", "user_123"), "preferences")
    ```
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.MEMORY_STORE_DB_PATH
        self._conn = None  # SQLite 连接
        self._pool = None  # PostgreSQL 连接池
        self._lock = asyncio.Lock()
        self._initialized = False
        self._backend = settings.DATABASE_BACKEND

    async def setup(self) -> None:
        """初始化数据库表"""
        if self._initialized:
            return

        settings.ensure_memory_dirs()

        if self._backend == "sqlite":
            await self._setup_sqlite()
        elif self._backend == "postgres":
            await self._setup_postgres()
        else:
            msg = f"不支持的数据库后端: {self._backend}"
            raise ValueError(msg)

        self._initialized = True
        logger.info("UserProfileStore 初始化完成", backend=self._backend)

    async def _setup_sqlite(self) -> None:
        """初始化 SQLite"""
        import aiosqlite

        self._conn = await aiosqlite.connect(self.db_path)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS store_items (
                namespace TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (namespace, key)
            )
        """)
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_store_namespace ON store_items(namespace)"
        )
        await self._conn.commit()

    async def _setup_postgres(self) -> None:
        """初始化 PostgreSQL"""
        import asyncpg

        conn_string = settings.checkpoint_connection_string
        self._pool = await asyncpg.create_pool(
            conn_string,
            min_size=1,
            max_size=settings.DATABASE_POOL_SIZE,
        )
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS store_items (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
            """)
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_store_namespace ON store_items(namespace)"
            )

    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
        if self._pool:
            await self._pool.close()
            self._pool = None
        self._initialized = False

    def _namespace_to_str(self, namespace: tuple[str, ...]) -> str:
        """将 namespace tuple 转为字符串"""
        return "/".join(namespace)

    def _str_to_namespace(self, ns_str: str) -> tuple[str, ...]:
        """将字符串转为 namespace tuple"""
        return tuple(ns_str.split("/"))

    async def put(
        self,
        namespace: tuple[str, ...],
        key: str,
        value: dict[str, Any],
    ) -> None:
        """写入条目"""
        await self.setup()
        async with self._lock:
            ns_str = self._namespace_to_str(namespace)
            now = datetime.now()

            if self._backend == "sqlite":
                await self._conn.execute(
                    """
                    INSERT INTO store_items (namespace, key, value, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(namespace, key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (ns_str, key, json.dumps(value, ensure_ascii=False), now.isoformat(), now.isoformat()),
                )
                await self._conn.commit()
            else:  # postgres
                async with self._pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO store_items (namespace, key, value, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT(namespace, key) DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = EXCLUDED.updated_at
                        """,
                        ns_str, key, json.dumps(value, ensure_ascii=False), now, now,
                    )

            logger.debug("Store put", namespace=ns_str, key=key)

    async def get(self, namespace: tuple[str, ...], key: str) -> Item | None:
        """读取条目"""
        await self.setup()
        ns_str = self._namespace_to_str(namespace)

        if self._backend == "sqlite":
            async with self._conn.execute(
                "SELECT value, created_at, updated_at FROM store_items WHERE namespace = ? AND key = ?",
                (ns_str, key),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Item(
                        namespace=namespace,
                        key=key,
                        value=json.loads(row[0]),
                        created_at=datetime.fromisoformat(row[1]),
                        updated_at=datetime.fromisoformat(row[2]),
                    )
        else:  # postgres
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT value, created_at, updated_at FROM store_items WHERE namespace = $1 AND key = $2",
                    ns_str, key,
                )
                if row:
                    value_data = row["value"]
                    if isinstance(value_data, str):
                        value_data = json.loads(value_data)
                    return Item(
                        namespace=namespace,
                        key=key,
                        value=value_data,
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
        return None

    async def delete(self, namespace: tuple[str, ...], key: str) -> bool:
        """删除条目"""
        await self.setup()
        async with self._lock:
            ns_str = self._namespace_to_str(namespace)

            if self._backend == "sqlite":
                cursor = await self._conn.execute(
                    "DELETE FROM store_items WHERE namespace = ? AND key = ?",
                    (ns_str, key),
                )
                await self._conn.commit()
                deleted = cursor.rowcount > 0
            else:  # postgres
                async with self._pool.acquire() as conn:
                    result = await conn.execute(
                        "DELETE FROM store_items WHERE namespace = $1 AND key = $2",
                        ns_str, key,
                    )
                    deleted = result != "DELETE 0"

            if deleted:
                logger.debug("Store delete", namespace=ns_str, key=key)
            return deleted

    async def search(
        self,
        namespace_prefix: tuple[str, ...],
        limit: int = 100,
        offset: int = 0,
    ) -> list[Item]:
        """搜索条目"""
        await self.setup()
        ns_prefix = self._namespace_to_str(namespace_prefix)
        if ns_prefix:
            ns_prefix += "/"

        items = []

        if self._backend == "sqlite":
            async with self._conn.execute(
                """
                SELECT namespace, key, value, created_at, updated_at
                FROM store_items
                WHERE namespace LIKE ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (ns_prefix + "%", limit, offset),
            ) as cursor:
                async for row in cursor:
                    items.append(
                        Item(
                            namespace=self._str_to_namespace(row[0]),
                            key=row[1],
                            value=json.loads(row[2]),
                            created_at=datetime.fromisoformat(row[3]),
                            updated_at=datetime.fromisoformat(row[4]),
                        )
                    )
        else:  # postgres
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT namespace, key, value, created_at, updated_at
                    FROM store_items
                    WHERE namespace LIKE $1
                    ORDER BY updated_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    ns_prefix + "%", limit, offset,
                )
                for row in rows:
                    value_data = row["value"]
                    if isinstance(value_data, str):
                        value_data = json.loads(value_data)
                    items.append(
                        Item(
                            namespace=self._str_to_namespace(row["namespace"]),
                            key=row["key"],
                            value=value_data,
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                        )
                    )

        return items

    async def list_namespaces(
        self,
        prefix: tuple[str, ...] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[str, ...]]:
        """列出所有命名空间"""
        await self.setup()

        if self._backend == "sqlite":
            query = "SELECT DISTINCT namespace FROM store_items"
            params: list[Any] = []

            if prefix:
                query += " WHERE namespace LIKE ?"
                params.append(self._namespace_to_str(prefix) + "/%")

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            async with self._conn.execute(query, params) as cursor:
                return [self._str_to_namespace(row[0]) async for row in cursor]
        else:  # postgres
            async with self._pool.acquire() as conn:
                if prefix:
                    rows = await conn.fetch(
                        "SELECT DISTINCT namespace FROM store_items WHERE namespace LIKE $1 LIMIT $2 OFFSET $3",
                        self._namespace_to_str(prefix) + "/%", limit, offset,
                    )
                else:
                    rows = await conn.fetch(
                        "SELECT DISTINCT namespace FROM store_items LIMIT $1 OFFSET $2",
                        limit, offset,
                    )
                return [self._str_to_namespace(row["namespace"]) for row in rows]

    # ========== 便捷方法 ==========

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """获取用户画像"""
        item = await self.get(("users", user_id), "profile")
        return item.value if item else None

    async def set_user_profile(self, user_id: str, profile: dict[str, Any]) -> None:
        """设置用户画像"""
        profile["updated_at"] = datetime.now().isoformat()
        await self.put(("users", user_id), "profile", profile)

    async def update_user_profile(
        self, user_id: str, updates: dict[str, Any]
    ) -> dict[str, Any]:
        """更新用户画像（合并更新）"""
        existing = await self.get_user_profile(user_id) or {}
        existing.update(updates)
        await self.set_user_profile(user_id, existing)
        return existing

    async def get_user_preference(
        self, user_id: str, key: str, default: Any = None
    ) -> Any:
        """获取用户特定偏好"""
        profile = await self.get_user_profile(user_id)
        if profile:
            return profile.get(key, default)
        return default

    async def set_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """设置用户特定偏好"""
        await self.update_user_profile(user_id, {key: value})

    async def get_task_progress(self, user_id: str, task_id: str) -> dict[str, Any] | None:
        """获取任务进度"""
        item = await self.get(("users", user_id, "tasks"), task_id)
        return item.value if item else None

    async def set_task_progress(
        self, user_id: str, task_id: str, progress: dict[str, Any]
    ) -> None:
        """设置任务进度"""
        progress["updated_at"] = datetime.now().isoformat()
        await self.put(("users", user_id, "tasks"), task_id, progress)


# 单例
_store_instance: UserProfileStore | None = None
_store_lock = asyncio.Lock()


async def get_user_profile_store() -> UserProfileStore:
    """获取 Store 单例"""
    global _store_instance
    if _store_instance is None:
        async with _store_lock:
            if _store_instance is None:
                _store_instance = UserProfileStore()
                await _store_instance.setup()
    return _store_instance
