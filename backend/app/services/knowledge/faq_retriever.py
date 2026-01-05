"""FAQ 检索器

基于向量相似度检索 FAQ 条目。
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger("knowledge.faq")


class FAQRetriever:
    """FAQ 检索器

    支持：
    1. 基于向量相似度检索
    2. 按 Agent 隔离 FAQ
    3. 可选 Rerank
    """

    def __init__(
        self,
        agent_id: str | None = None,
        collection_name: str | None = None,
        top_k: int = 10,
        similarity_threshold: float | None = None,
    ):
        self.agent_id = agent_id
        self.collection_name = collection_name or "faq_entries"
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def search(self, query: str) -> list[dict[str, Any]]:
        """检索相关 FAQ

        Args:
            query: 查询问题

        Returns:
            FAQ 条目列表，每个包含 question, answer, category, score 等
        """
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        from app.core.config import settings
        from app.core.embedding import get_embedding_model

        try:
            # 1. 获取查询向量
            embedding_model = get_embedding_model()
            query_vector = await embedding_model.aembed_query(query)

            # 2. 构建过滤条件（按 Agent 隔离）
            filter_conditions = []
            if self.agent_id:
                filter_conditions.append(
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=self.agent_id),
                    )
                )
            # 只检索启用的 FAQ
            filter_conditions.append(
                FieldCondition(
                    key="enabled",
                    match=MatchValue(value=True),
                )
            )

            search_filter = Filter(must=filter_conditions) if filter_conditions else None

            # 3. 执行向量检索
            client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

            results = await client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=self.top_k,
                score_threshold=self.similarity_threshold,
            )

            # 4. 格式化结果
            faq_items: list[dict[str, Any]] = []
            for hit in results:
                payload = hit.payload or {}
                faq_items.append(
                    {
                        "id": payload.get("id"),
                        "question": payload.get("question", ""),
                        "answer": payload.get("answer", ""),
                        "category": payload.get("category"),
                        "tags": payload.get("tags", []),
                        "source": payload.get("source"),
                        "score": hit.score,
                    }
                )

            logger.debug(
                "FAQ 检索完成",
                query=query[:50],
                result_count=len(faq_items),
                agent_id=self.agent_id,
            )

            return faq_items

        except Exception as e:
            logger.error("FAQ 检索失败", error=str(e), query=query[:50])
            raise

    async def index_entries(self, entries: list[dict[str, Any]]) -> int:
        """索引 FAQ 条目到向量库

        Args:
            entries: FAQ 条目列表

        Returns:
            成功索引的数量
        """
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        from app.core.config import settings
        from app.core.embedding import get_embedding_model

        if not entries:
            return 0

        try:
            embedding_model = get_embedding_model()
            client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

            # 确保集合存在
            collections = await client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                await client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info("创建 FAQ 集合", collection_name=self.collection_name)

            # 批量生成向量
            questions = [e.get("question", "") for e in entries]
            vectors = await embedding_model.aembed_documents(questions)

            # 构建 points
            points = []
            for i, (entry, vector) in enumerate(zip(entries, vectors)):
                point = PointStruct(
                    id=entry.get("id") or str(i),
                    vector=vector,
                    payload={
                        "id": entry.get("id"),
                        "question": entry.get("question", ""),
                        "answer": entry.get("answer", ""),
                        "category": entry.get("category"),
                        "tags": entry.get("tags", []),
                        "source": entry.get("source"),
                        "agent_id": self.agent_id,
                        "enabled": entry.get("enabled", True),
                    },
                )
                points.append(point)

            # 上传到 Qdrant
            await client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(
                "FAQ 索引完成",
                indexed_count=len(points),
                collection_name=self.collection_name,
            )

            return len(points)

        except Exception as e:
            logger.error("FAQ 索引失败", error=str(e))
            raise
