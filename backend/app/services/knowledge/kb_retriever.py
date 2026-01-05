"""知识库检索器

基于向量相似度检索内部知识库文档。
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger("knowledge.kb")


class KBRetriever:
    """知识库检索器

    支持：
    1. 基于向量相似度检索
    2. 可选 Rerank 重排序
    3. 多种文档类型
    """

    def __init__(
        self,
        collection_name: str | None = None,
        top_k: int = 10,
        rerank_enabled: bool = False,
        similarity_threshold: float | None = None,
    ):
        self.collection_name = collection_name or "knowledge_base"
        self.top_k = top_k
        self.rerank_enabled = rerank_enabled
        self.similarity_threshold = similarity_threshold

    async def search(self, query: str) -> list[dict[str, Any]]:
        """检索相关文档

        Args:
            query: 查询问题

        Returns:
            文档列表，每个包含 content, source, score 等
        """
        from qdrant_client import AsyncQdrantClient

        from app.core.config import settings
        from app.core.embedding import get_embedding_model

        try:
            # 1. 获取查询向量
            embedding_model = get_embedding_model()
            query_vector = await embedding_model.aembed_query(query)

            # 2. 执行向量检索
            client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
            )

            # 检索更多结果以便 rerank
            search_limit = self.top_k * 3 if self.rerank_enabled else self.top_k

            results = await client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=search_limit,
                score_threshold=self.similarity_threshold,
            )

            # 3. 格式化结果
            documents: list[dict[str, Any]] = []
            for hit in results:
                payload = hit.payload or {}
                documents.append(
                    {
                        "id": payload.get("id"),
                        "content": payload.get("content", ""),
                        "source": payload.get("source"),
                        "title": payload.get("title"),
                        "metadata": payload.get("metadata", {}),
                        "score": hit.score,
                    }
                )

            # 4. 可选 Rerank
            if self.rerank_enabled and documents:
                documents = await self._rerank(query, documents)

            # 5. 截取 top_k
            documents = documents[: self.top_k]

            logger.debug(
                "知识库检索完成",
                query=query[:50],
                result_count=len(documents),
                reranked=self.rerank_enabled,
            )

            return documents

        except Exception as e:
            logger.error("知识库检索失败", error=str(e), query=query[:50])
            raise

    async def _rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """使用 Rerank 模型重排序

        Args:
            query: 查询问题
            documents: 初步检索结果

        Returns:
            重排序后的文档列表
        """
        from app.core.config import settings

        if not settings.RERANK_ENABLED or not settings.RERANK_MODEL:
            return documents

        try:
            from app.core.rerank import rerank_documents

            # 提取文档内容
            doc_contents = [d.get("content", "") for d in documents]

            # 调用 rerank
            reranked_indices = await rerank_documents(
                query=query,
                documents=doc_contents,
                top_n=len(documents),
            )

            # 按新顺序重排
            reranked_docs = [documents[i] for i in reranked_indices]

            logger.debug(
                "Rerank 完成",
                original_count=len(documents),
                reranked_count=len(reranked_docs),
            )

            return reranked_docs

        except Exception as e:
            logger.warning("Rerank 失败，返回原始结果", error=str(e))
            return documents

    async def index_documents(self, documents: list[dict[str, Any]]) -> int:
        """索引文档到向量库

        Args:
            documents: 文档列表，每个包含 id, content, source, title, metadata

        Returns:
            成功索引的数量
        """
        from qdrant_client import AsyncQdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        from app.core.config import settings
        from app.core.embedding import get_embedding_model

        if not documents:
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
                logger.info("创建知识库集合", collection_name=self.collection_name)

            # 批量生成向量
            contents = [d.get("content", "") for d in documents]
            vectors = await embedding_model.aembed_documents(contents)

            # 构建 points
            points = []
            for i, (doc, vector) in enumerate(zip(documents, vectors)):
                point = PointStruct(
                    id=doc.get("id") or str(i),
                    vector=vector,
                    payload={
                        "id": doc.get("id"),
                        "content": doc.get("content", ""),
                        "source": doc.get("source"),
                        "title": doc.get("title"),
                        "metadata": doc.get("metadata", {}),
                    },
                )
                points.append(point)

            # 上传到 Qdrant
            await client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(
                "知识库索引完成",
                indexed_count=len(points),
                collection_name=self.collection_name,
            )

            return len(points)

        except Exception as e:
            logger.error("知识库索引失败", error=str(e))
            raise
