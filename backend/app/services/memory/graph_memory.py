"""图谱记忆 - Python 原生实现

基于 docs/图关系记忆参考.md 的 JS 逻辑，提供 Python 版本的 KnowledgeGraphManager。

功能：
- 实体/关系/观察的 CRUD 操作
- 基于关键词的搜索
- JSONL 格式持久化存储
- 支持按用户隔离（通过 user_id 作为实体前缀或观察标记）
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.memory.models import Entity, KnowledgeGraph, Relation
from app.services.memory.prompts import GRAPH_EXTRACTION_PROMPT

logger = get_logger("memory.graph")


class KnowledgeGraphManager:
    """知识图谱管理器

    用法：
    ```python
    manager = await get_graph_manager()

    # 创建实体
    await manager.create_entities([
        Entity(name="用户A", entity_type="PERSON", observations=["喜欢科技产品"])
    ])

    # 创建关系
    await manager.create_relations([
        Relation(from_entity="用户A", to_entity="iPhone", relation_type="PREFERS")
    ])

    # 搜索
    graph = await manager.search_nodes("科技")
    ```
    """

    def __init__(self, file_path: str | None = None):
        self.file_path = file_path or settings.MEMORY_GRAPH_FILE_PATH
        self._lock = asyncio.Lock()

    async def _load_graph(self) -> KnowledgeGraph:
        """加载图谱"""
        path = Path(self.file_path)
        if not path.exists():
            return KnowledgeGraph()

        entities: list[Entity] = []
        relations: list[Relation] = []

        try:
            content = path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if item.get("type") == "entity":
                        entities.append(
                            Entity(
                                name=item["name"],
                                entity_type=item["entity_type"],
                                observations=item.get("observations", []),
                            )
                        )
                    elif item.get("type") == "relation":
                        relations.append(
                            Relation(
                                from_entity=item["from_entity"],
                                to_entity=item["to_entity"],
                                relation_type=item["relation_type"],
                            )
                        )
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("解析图谱行失败", error=str(e), line=line[:50])
                    continue
        except Exception as e:
            logger.warning("加载图谱失败", error=str(e))

        return KnowledgeGraph(entities=entities, relations=relations)

    async def _save_graph(self, graph: KnowledgeGraph) -> None:
        """保存图谱"""
        settings.ensure_memory_dirs()

        lines = []
        for e in graph.entities:
            lines.append(
                json.dumps(
                    {
                        "type": "entity",
                        "name": e.name,
                        "entity_type": e.entity_type,
                        "observations": e.observations,
                    },
                    ensure_ascii=False,
                )
            )

        for r in graph.relations:
            lines.append(
                json.dumps(
                    {
                        "type": "relation",
                        "from_entity": r.from_entity,
                        "to_entity": r.to_entity,
                        "relation_type": r.relation_type,
                    },
                    ensure_ascii=False,
                )
            )

        path = Path(self.file_path)
        path.write_text("\n".join(lines), encoding="utf-8")

    async def create_entities(self, entities: list[Entity]) -> list[Entity]:
        """创建实体（去重）

        Args:
            entities: 要创建的实体列表

        Returns:
            实际创建的新实体列表
        """
        if not entities:
            return []

        async with self._lock:
            graph = await self._load_graph()
            existing_names = {e.name for e in graph.entities}
            new_entities = [e for e in entities if e.name not in existing_names]

            if new_entities:
                graph.entities.extend(new_entities)
                await self._save_graph(graph)
                logger.info("创建实体", count=len(new_entities))

            return new_entities

    async def create_relations(self, relations: list[Relation]) -> list[Relation]:
        """创建关系（去重）

        Args:
            relations: 要创建的关系列表

        Returns:
            实际创建的新关系列表
        """
        if not relations:
            return []

        async with self._lock:
            graph = await self._load_graph()
            existing = {
                (r.from_entity, r.to_entity, r.relation_type) for r in graph.relations
            }
            new_relations = [
                r
                for r in relations
                if (r.from_entity, r.to_entity, r.relation_type) not in existing
            ]

            if new_relations:
                graph.relations.extend(new_relations)
                await self._save_graph(graph)
                logger.info("创建关系", count=len(new_relations))

            return new_relations

    async def add_observations(
        self,
        observations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """添加观察到实体

        Args:
            observations: 观察列表，格式 [{"entity_name": "xxx", "contents": ["观察1", "观察2"]}]

        Returns:
            实际添加的观察结果
        """
        if not observations:
            return []

        async with self._lock:
            graph = await self._load_graph()
            results = []

            for obs in observations:
                entity_name = obs.get("entity_name")
                contents = obs.get("contents", [])

                if not entity_name or not contents:
                    continue

                entity = next(
                    (e for e in graph.entities if e.name == entity_name), None
                )
                if not entity:
                    logger.warning("实体不存在", entity_name=entity_name)
                    continue

                new_obs = [c for c in contents if c not in entity.observations]
                entity.observations.extend(new_obs)
                results.append(
                    {
                        "entity_name": entity_name,
                        "added_observations": new_obs,
                    }
                )

            if results:
                await self._save_graph(graph)
                logger.info("添加观察", count=sum(len(r["added_observations"]) for r in results))

            return results

    async def delete_entities(self, entity_names: list[str]) -> int:
        """删除实体及其关联关系

        Args:
            entity_names: 要删除的实体名称列表

        Returns:
            删除的实体数量
        """
        if not entity_names:
            return 0

        async with self._lock:
            graph = await self._load_graph()
            names_set = set(entity_names)

            original_count = len(graph.entities)
            graph.entities = [e for e in graph.entities if e.name not in names_set]
            graph.relations = [
                r
                for r in graph.relations
                if r.from_entity not in names_set and r.to_entity not in names_set
            ]

            deleted_count = original_count - len(graph.entities)
            if deleted_count > 0:
                await self._save_graph(graph)
                logger.info("删除实体", count=deleted_count)

            return deleted_count

    async def delete_observations(
        self, deletions: list[dict[str, Any]]
    ) -> int:
        """删除实体的观察

        Args:
            deletions: 删除列表，格式 [{"entity_name": "xxx", "observations": ["观察1"]}]

        Returns:
            删除的观察数量
        """
        if not deletions:
            return 0

        async with self._lock:
            graph = await self._load_graph()
            deleted_count = 0

            for d in deletions:
                entity_name = d.get("entity_name")
                obs_to_delete = set(d.get("observations", []))

                entity = next(
                    (e for e in graph.entities if e.name == entity_name), None
                )
                if entity:
                    original_len = len(entity.observations)
                    entity.observations = [
                        o for o in entity.observations if o not in obs_to_delete
                    ]
                    deleted_count += original_len - len(entity.observations)

            if deleted_count > 0:
                await self._save_graph(graph)
                logger.info("删除观察", count=deleted_count)

            return deleted_count

    async def delete_relations(self, relations: list[Relation]) -> int:
        """删除关系

        Args:
            relations: 要删除的关系列表

        Returns:
            删除的关系数量
        """
        if not relations:
            return 0

        async with self._lock:
            graph = await self._load_graph()
            to_delete = {
                (r.from_entity, r.to_entity, r.relation_type) for r in relations
            }

            original_count = len(graph.relations)
            graph.relations = [
                r
                for r in graph.relations
                if (r.from_entity, r.to_entity, r.relation_type) not in to_delete
            ]

            deleted_count = original_count - len(graph.relations)
            if deleted_count > 0:
                await self._save_graph(graph)
                logger.info("删除关系", count=deleted_count)

            return deleted_count

    async def read_graph(self) -> KnowledgeGraph:
        """读取完整图谱"""
        return await self._load_graph()

    async def search_nodes(self, query: str) -> KnowledgeGraph:
        """搜索节点

        基于关键词匹配实体名称、类型和观察内容

        Args:
            query: 搜索查询

        Returns:
            匹配的子图
        """
        graph = await self._load_graph()
        query_lower = query.lower()

        filtered_entities = [
            e
            for e in graph.entities
            if (
                query_lower in e.name.lower()
                or query_lower in e.entity_type.lower()
                or any(query_lower in obs.lower() for obs in e.observations)
            )
        ]

        entity_names = {e.name for e in filtered_entities}
        filtered_relations = [
            r
            for r in graph.relations
            if r.from_entity in entity_names and r.to_entity in entity_names
        ]

        return KnowledgeGraph(entities=filtered_entities, relations=filtered_relations)

    async def open_nodes(self, names: list[str]) -> KnowledgeGraph:
        """打开指定节点

        Args:
            names: 实体名称列表

        Returns:
            包含指定实体及其关系的子图
        """
        graph = await self._load_graph()
        names_set = set(names)

        filtered_entities = [e for e in graph.entities if e.name in names_set]
        entity_names = {e.name for e in filtered_entities}
        filtered_relations = [
            r
            for r in graph.relations
            if r.from_entity in entity_names and r.to_entity in entity_names
        ]

        return KnowledgeGraph(entities=filtered_entities, relations=filtered_relations)

    async def get_entity(self, name: str) -> Entity | None:
        """获取单个实体"""
        graph = await self._load_graph()
        return next((e for e in graph.entities if e.name == name), None)

    async def get_entity_relations(self, entity_name: str) -> list[Relation]:
        """获取实体的所有关系"""
        graph = await self._load_graph()
        return [
            r
            for r in graph.relations
            if r.from_entity == entity_name or r.to_entity == entity_name
        ]

    async def get_related_entities(self, entity_name: str) -> list[Entity]:
        """获取与实体相关的所有实体"""
        graph = await self._load_graph()
        related_names = set()

        for r in graph.relations:
            if r.from_entity == entity_name:
                related_names.add(r.to_entity)
            elif r.to_entity == entity_name:
                related_names.add(r.from_entity)

        return [e for e in graph.entities if e.name in related_names]

    async def extract_and_save(
        self, user_id: str, messages: list[dict[str, str]]
    ) -> tuple[int, int]:
        """从对话中抽取实体和关系并保存

        Args:
            user_id: 用户 ID（用于标记）
            messages: 对话消息列表

        Returns:
            (新增实体数, 新增关系数)
        """
        if not settings.MEMORY_GRAPH_ENABLED:
            return 0, 0

        if not messages:
            return 0, 0

        start_time = time.perf_counter()
        logger.debug(
            "graph.extract.start",
            user_id=user_id,
            message_count=len(messages),
        )

        try:
            llm_start = time.perf_counter()
            from app.core.llm import get_memory_model

            model = get_memory_model()

            recent_messages = messages[-10:]
            conversation = "\n".join(
                [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in recent_messages]
            )

            response = await model.ainvoke(
                [
                    {"role": "system", "content": GRAPH_EXTRACTION_PROMPT},
                    {"role": "user", "content": conversation},
                ]
            )
            llm_elapsed = int((time.perf_counter() - llm_start) * 1000)
            logger.debug(
                "graph.extract.llm_complete",
                user_id=user_id,
                llm_elapsed_ms=llm_elapsed,
                message_count=len(recent_messages),
            )

            content = response.content
            if isinstance(content, str):
                content = content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

                parse_start = time.perf_counter()
                try:
                    data = json.loads(content)
                    parse_elapsed = int((time.perf_counter() - parse_start) * 1000)
                    logger.debug(
                        "graph.extract.parse_complete",
                        user_id=user_id,
                        parse_elapsed_ms=parse_elapsed,
                        entity_count=len(data.get("entities", [])),
                        relation_count=len(data.get("relations", [])),
                    )

                    # 解析实体
                    entities = []
                    for e in data.get("entities", []):
                        if isinstance(e, dict) and e.get("name"):
                            # 添加用户标记到观察
                            observations = e.get("observations", [])
                            observations.append(f"[user:{user_id}]")
                            entities.append(
                                Entity(
                                    name=e["name"],
                                    entity_type=e.get("entity_type", "UNKNOWN"),
                                    observations=observations,
                                )
                            )

                    # 解析关系
                    relations = []
                    for r in data.get("relations", []):
                        if (
                            isinstance(r, dict)
                            and r.get("from_entity")
                            and r.get("to_entity")
                        ):
                            relations.append(
                                Relation(
                                    from_entity=r["from_entity"],
                                    to_entity=r["to_entity"],
                                    relation_type=r.get("relation_type", "RELATED_TO"),
                                )
                            )

                    # 保存
                    write_start = time.perf_counter()
                    new_entities = await self.create_entities(entities)
                    new_relations = await self.create_relations(relations)
                    write_elapsed = int((time.perf_counter() - write_start) * 1000)

                    logger.info(
                        "图谱抽取完成",
                        user_id=user_id,
                        new_entities=len(new_entities),
                        new_relations=len(new_relations),
                        llm_elapsed_ms=llm_elapsed,
                        parse_elapsed_ms=parse_elapsed,
                        write_elapsed_ms=write_elapsed,
                        total_elapsed_ms=int((time.perf_counter() - start_time) * 1000),
                    )

                    return len(new_entities), len(new_relations)

                except json.JSONDecodeError:
                    logger.warning("图谱抽取 JSON 解析失败", content_preview=content[:100])

            return 0, 0

        except Exception as e:
            logger.error("图谱抽取失败", error=str(e), user_id=user_id)
            return 0, 0

    async def get_user_graph(self, user_id: str) -> KnowledgeGraph:
        """获取用户相关的图谱

        通过观察中的 [user:xxx] 标记过滤

        Args:
            user_id: 用户 ID

        Returns:
            用户相关的子图
        """
        graph = await self._load_graph()
        user_marker = f"[user:{user_id}]"

        filtered_entities = [
            e
            for e in graph.entities
            if any(user_marker in obs for obs in e.observations)
        ]

        entity_names = {e.name for e in filtered_entities}
        filtered_relations = [
            r
            for r in graph.relations
            if r.from_entity in entity_names or r.to_entity in entity_names
        ]

        # 扩展：包含关系连接的实体
        extended_names = entity_names.copy()
        for r in filtered_relations:
            extended_names.add(r.from_entity)
            extended_names.add(r.to_entity)

        extended_entities = [e for e in graph.entities if e.name in extended_names]

        return KnowledgeGraph(entities=extended_entities, relations=filtered_relations)


# 单例
_graph_manager: KnowledgeGraphManager | None = None
_graph_lock = asyncio.Lock()


async def get_graph_manager() -> KnowledgeGraphManager:
    """获取 KnowledgeGraphManager 单例"""
    global _graph_manager
    if _graph_manager is None:
        async with _graph_lock:
            if _graph_manager is None:
                _graph_manager = KnowledgeGraphManager()
    return _graph_manager
