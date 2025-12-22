"""事实型长期记忆服务

借鉴 Cherry Studio MemoryService：LLM 事实抽取 → 哈希去重 → Qdrant 向量检索

流程：
1. 对话结束后调用 extract_facts 从对话中抽取事实
2. 对每条事实调用 decide_action 决定操作（ADD/UPDATE/DELETE/NONE）
3. 执行对应操作，写入 SQLite（元数据/历史）+ Qdrant（向量）
4. 检索时调用 search_facts，由 Qdrant 完成向量相似度计算
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any

import aiosqlite
from langchain_core.documents import Document
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.logging import get_logger
from app.services.memory.models import Fact, MemoryAction
from app.services.memory.prompts import FACT_EXTRACTION_PROMPT, MEMORY_ACTION_PROMPT
from app.services.memory.vector_store import get_memory_vector_store

logger = get_logger("memory.fact")


def _compute_hash(content: str) -> str:
    """计算内容 SHA256 哈希"""
    return hashlib.sha256(content.strip().encode()).hexdigest()


class FactMemoryService:
    """事实型长期记忆服务

    用法：
    ```python
    service = await get_fact_memory_service()

    # 从对话抽取事实
    facts = await service.extract_facts("user_123", messages)

    # 添加事实
    for fact_content in facts:
        await service.add_fact("user_123", fact_content)

    # 搜索相关事实
    results = await service.search_facts("user_123", "预算")
    ```
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.MEMORY_FACT_DB_PATH
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()
        self._initialized = False
        self._vector_store = None

    async def setup(self) -> None:
        """初始化数据库"""
        if self._initialized:
            return

        settings.ensure_memory_dirs()
        self._conn = await aiosqlite.connect(self.db_path)

        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS fact_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id TEXT NOT NULL,
                action TEXT NOT NULL,
                old_content TEXT,
                new_content TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_facts_hash ON facts(hash)"
        )
        await self._conn.commit()

        # 初始化 Qdrant 向量存储
        self._vector_store = get_memory_vector_store()

        self._initialized = True
        logger.info(
            "FactMemoryService 初始化完成",
            db_path=self.db_path,
            qdrant_collection=settings.MEMORY_FACT_COLLECTION,
        )

    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            self._initialized = False

    async def _get_chat_model(self):
        """获取聊天模型"""
        from app.core.llm import get_chat_model

        return get_chat_model()

    async def extract_facts(
        self, user_id: str, messages: list[dict[str, str]]
    ) -> list[str]:
        """从对话中抽取事实

        Args:
            user_id: 用户 ID
            messages: 对话消息列表，格式 [{"role": "user", "content": "..."}]

        Returns:
            抽取的事实列表
        """
        if not settings.MEMORY_FACT_ENABLED:
            return []

        if not messages:
            return []

        try:
            model = await self._get_chat_model()

            # 只处理最近的消息
            recent_messages = messages[-10:]
            conversation = "\n".join(
                [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent_messages]
            )

            response = await model.ainvoke(
                [
                    {"role": "system", "content": FACT_EXTRACTION_PROMPT},
                    {"role": "user", "content": conversation},
                ]
            )

            content = response.content
            if isinstance(content, str):
                # 尝试提取 JSON
                content = content.strip()
                # 处理可能的 markdown code block
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

                try:
                    data = json.loads(content)
                    facts = data.get("facts", [])
                    if isinstance(facts, list):
                        logger.info(
                            "事实抽取完成", user_id=user_id, fact_count=len(facts)
                        )
                        return [f for f in facts if isinstance(f, str) and f.strip()]
                except json.JSONDecodeError:
                    logger.warning("事实抽取 JSON 解析失败", content_preview=content[:100])

            return []

        except Exception as e:
            logger.error("事实抽取失败", error=str(e), user_id=user_id)
            return []

    async def decide_action(
        self,
        user_id: str,
        new_fact: str,
        existing_facts: list[Fact] | None = None,
    ) -> tuple[MemoryAction, str | None]:
        """决定记忆操作

        Args:
            user_id: 用户 ID
            new_fact: 新事实
            existing_facts: 相关的现有事实（如为 None 则自动搜索）

        Returns:
            (操作类型, 目标事实ID)
        """
        if existing_facts is None:
            existing_facts = await self.search_facts(user_id, new_fact, limit=5)

        if not existing_facts:
            return MemoryAction.ADD, None

        try:
            model = await self._get_chat_model()
            existing_str = "\n".join(
                [f"[{f.id[:8]}] {f.content}" for f in existing_facts[:5]]
            )

            response = await model.ainvoke(
                [
                    {"role": "system", "content": MEMORY_ACTION_PROMPT},
                    {
                        "role": "user",
                        "content": f"新事实：{new_fact}\n\n现有记忆：\n{existing_str}",
                    },
                ]
            )

            content = response.content
            if isinstance(content, str):
                content = content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

                try:
                    data = json.loads(content)
                    action_str = data.get("action", "NONE").upper()
                    action = (
                        MemoryAction(action_str)
                        if action_str in MemoryAction.__members__
                        else MemoryAction.NONE
                    )
                    target_id = data.get("target_id")

                    # 如果是 UPDATE/DELETE，需要匹配完整的 fact_id
                    if target_id and action in (MemoryAction.UPDATE, MemoryAction.DELETE):
                        matched = next(
                            (f for f in existing_facts if f.id.startswith(target_id)),
                            None,
                        )
                        if matched:
                            return action, matched.id

                    return action, None

                except (json.JSONDecodeError, ValueError):
                    pass

            return MemoryAction.ADD, None

        except Exception as e:
            logger.error("行为判定失败", error=str(e))
            return MemoryAction.NONE, None

    async def add_fact(
        self,
        user_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Fact | None:
        """添加新事实

        Args:
            user_id: 用户 ID
            content: 事实内容
            metadata: 额外元数据

        Returns:
            创建的 Fact 对象，如果重复则返回 None
        """
        await self.setup()

        content = content.strip()
        if not content:
            return None

        content_hash = _compute_hash(content)

        async with self._lock:
            # 检查哈希去重
            async with self._conn.execute(
                "SELECT id FROM facts WHERE user_id = ? AND hash = ?",
                (user_id, content_hash),
            ) as cursor:
                if await cursor.fetchone():
                    logger.debug("事实已存在（哈希重复）", hash=content_hash[:16])
                    return None

            fact_id = hashlib.md5(
                f"{user_id}:{content}:{datetime.now().isoformat()}".encode()
            ).hexdigest()
            now = datetime.now().isoformat()

            # 写入 SQLite（元数据）
            await self._conn.execute(
                """
                INSERT INTO facts (id, user_id, content, hash, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    user_id,
                    content,
                    content_hash,
                    now,
                    now,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )

            # 记录历史
            await self._conn.execute(
                """
                INSERT INTO fact_history (fact_id, action, new_content, created_at)
                VALUES (?, 'ADD', ?, ?)
                """,
                (fact_id, content, now),
            )

            await self._conn.commit()

            # 写入 Qdrant（向量）
            doc = Document(
                page_content=content,
                metadata={
                    "fact_id": fact_id,
                    "user_id": user_id,
                    "hash": content_hash,
                    "created_at": now,
                },
            )
            await asyncio.to_thread(self._vector_store.add_documents, [doc])

            logger.info("添加新事实", fact_id=fact_id[:8], content_preview=content[:50])

            return Fact(
                id=fact_id,
                user_id=user_id,
                content=content,
                hash=content_hash,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
                metadata=metadata or {},
            )

    async def update_fact(
        self, fact_id: str, new_content: str
    ) -> Fact | None:
        """更新事实内容"""
        await self.setup()

        new_content = new_content.strip()
        if not new_content:
            return None

        async with self._lock:
            # 获取原事实
            async with self._conn.execute(
                "SELECT user_id, content FROM facts WHERE id = ?", (fact_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    logger.warning("事实不存在", fact_id=fact_id)
                    return None
                user_id, old_content = row

            now = datetime.now().isoformat()
            new_hash = _compute_hash(new_content)

            # 更新 SQLite
            await self._conn.execute(
                """
                UPDATE facts SET content = ?, hash = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_content, new_hash, now, fact_id),
            )

            await self._conn.execute(
                """
                INSERT INTO fact_history (fact_id, action, old_content, new_content, created_at)
                VALUES (?, 'UPDATE', ?, ?, ?)
                """,
                (fact_id, old_content, new_content, now),
            )

            await self._conn.commit()

            # 更新 Qdrant：先删除旧向量，再添加新向量
            try:
                from app.services.memory.vector_store import get_memory_qdrant_client

                client = get_memory_qdrant_client()
                # 按 fact_id 删除旧记录
                client.delete(
                    collection_name=settings.MEMORY_FACT_COLLECTION,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="metadata.fact_id", match=MatchValue(value=fact_id)
                            )
                        ]
                    ),
                )
            except Exception as e:
                logger.warning("删除旧向量失败", error=str(e))

            # 添加新向量
            doc = Document(
                page_content=new_content,
                metadata={
                    "fact_id": fact_id,
                    "user_id": user_id,
                    "hash": new_hash,
                    "created_at": now,
                },
            )
            await asyncio.to_thread(self._vector_store.add_documents, [doc])

            logger.info("更新事实", fact_id=fact_id[:8])

            return Fact(
                id=fact_id,
                user_id=user_id,
                content=new_content,
                hash=new_hash,
                updated_at=datetime.fromisoformat(now),
            )

    async def delete_fact(self, fact_id: str) -> bool:
        """删除事实（记录历史）"""
        await self.setup()

        async with self._lock:
            async with self._conn.execute(
                "SELECT content FROM facts WHERE id = ?", (fact_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                old_content = row[0]

            now = datetime.now().isoformat()

            # 删除 SQLite 记录
            await self._conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))

            await self._conn.execute(
                """
                INSERT INTO fact_history (fact_id, action, old_content, created_at)
                VALUES (?, 'DELETE', ?, ?)
                """,
                (fact_id, old_content, now),
            )

            await self._conn.commit()

            # 删除 Qdrant 向量
            try:
                from app.services.memory.vector_store import get_memory_qdrant_client

                client = get_memory_qdrant_client()
                client.delete(
                    collection_name=settings.MEMORY_FACT_COLLECTION,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="metadata.fact_id", match=MatchValue(value=fact_id)
                            )
                        ]
                    ),
                )
            except Exception as e:
                logger.warning("删除向量失败", error=str(e))

            logger.info("删除事实", fact_id=fact_id[:8])
            return True

    async def search_facts(
        self,
        user_id: str,
        query: str,
        limit: int | None = None,
        threshold: float | None = None,
    ) -> list[Fact]:
        """搜索相关事实（使用 Qdrant 向量检索）

        Args:
            user_id: 用户 ID
            query: 搜索查询
            limit: 最大返回数量
            threshold: 相似度阈值

        Returns:
            匹配的事实列表（按相似度降序）
        """
        await self.setup()

        limit = limit or settings.MEMORY_FACT_MAX_RESULTS
        threshold = threshold or settings.MEMORY_FACT_SIMILARITY_THRESHOLD

        # 使用 Qdrant 向量检索
        try:
            # 构建 user_id 过滤条件
            user_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.user_id", match=MatchValue(value=user_id)
                    )
                ]
            )

            # 执行相似度搜索（Qdrant 负责向量计算）
            results = await asyncio.to_thread(
                self._vector_store.similarity_search_with_score,
                query,
                k=limit,
                filter=user_filter,
            )

            # 转换为 Fact 对象
            facts = []
            for doc, score in results:
                # Qdrant 返回的是距离（越小越相似），score 越大代表越不相关
                if score > threshold:
                    continue

                metadata = doc.metadata or {}
                fact_id = metadata.get("fact_id", "")

                # 从 SQLite 获取完整元数据
                async with self._conn.execute(
                    "SELECT created_at, updated_at, metadata FROM facts WHERE id = ?",
                    (fact_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        facts.append(
                            Fact(
                                id=fact_id,
                                user_id=user_id,
                                content=doc.page_content,
                                hash=metadata.get("hash", ""),
                                created_at=datetime.fromisoformat(row[0]),
                                updated_at=datetime.fromisoformat(row[1]),
                                metadata=json.loads(row[2]) if row[2] else {},
                            )
                        )

            return facts

        except Exception as e:
            logger.warning("向量检索失败，回退到关键词搜索", error=str(e))
            # 回退到 SQLite 关键词搜索
            return await self._fallback_keyword_search(user_id, query, limit)

    async def _fallback_keyword_search(
        self, user_id: str, query: str, limit: int
    ) -> list[Fact]:
        """关键词搜索回退（当 Qdrant 不可用时）"""
        query_lower = query.lower()
        facts = []

        async with self._conn.execute(
            "SELECT id, user_id, content, hash, created_at, updated_at, metadata "
            "FROM facts WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            async for row in cursor:
                if query_lower in row[2].lower():
                    facts.append(
                        Fact(
                            id=row[0],
                            user_id=row[1],
                            content=row[2],
                            hash=row[3],
                            created_at=datetime.fromisoformat(row[4]),
                            updated_at=datetime.fromisoformat(row[5]),
                            metadata=json.loads(row[6]) if row[6] else {},
                        )
                    )
                    if len(facts) >= limit:
                        break

        return facts

    async def get_all_facts(self, user_id: str) -> list[Fact]:
        """获取用户所有事实"""
        await self.setup()

        async with self._conn.execute(
            """
            SELECT id, user_id, content, hash, created_at, updated_at, metadata
            FROM facts WHERE user_id = ? ORDER BY updated_at DESC
            """,
            (user_id,),
        ) as cursor:
            facts = []
            async for row in cursor:
                facts.append(
                    Fact(
                        id=row[0],
                        user_id=row[1],
                        content=row[2],
                        hash=row[3],
                        created_at=datetime.fromisoformat(row[4]),
                        updated_at=datetime.fromisoformat(row[5]),
                        metadata=json.loads(row[6]) if row[6] else {},
                    )
                )
            return facts

    async def process_conversation(
        self, user_id: str, messages: list[dict[str, str]]
    ) -> int:
        """处理对话，抽取并存储事实

        Args:
            user_id: 用户 ID
            messages: 对话消息列表

        Returns:
            新增的事实数量
        """
        facts = await self.extract_facts(user_id, messages)
        added_count = 0

        for fact_content in facts:
            action, target_id = await self.decide_action(user_id, fact_content)

            if action == MemoryAction.ADD:
                result = await self.add_fact(user_id, fact_content)
                if result:
                    added_count += 1
            elif action == MemoryAction.UPDATE and target_id:
                await self.update_fact(target_id, fact_content)
            elif action == MemoryAction.DELETE and target_id:
                await self.delete_fact(target_id)

        return added_count


# 单例
_fact_service: FactMemoryService | None = None
_fact_lock = asyncio.Lock()


async def get_fact_memory_service() -> FactMemoryService:
    """获取 FactMemoryService 单例"""
    global _fact_service
    if _fact_service is None:
        async with _fact_lock:
            if _fact_service is None:
                _fact_service = FactMemoryService()
                await _fact_service.setup()
    return _fact_service
