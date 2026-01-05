"""知识源检索器工厂

根据 KnowledgeConfig 创建对应的检索器实例。
"""

from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import KnowledgeConfigResponse

logger = get_logger("knowledge.factory")


def create_retriever(
    knowledge_config: "KnowledgeConfigResponse",
    agent_id: str | None = None,
) -> Any:
    """根据知识源配置创建检索器

    Args:
        knowledge_config: 知识源配置
        agent_id: 可选的 Agent ID（用于 FAQ 隔离）

    Returns:
        检索器实例

    Raises:
        ValueError: 不支持的知识源类型
    """
    knowledge_type = knowledge_config.type

    if knowledge_type == "faq":
        from app.services.knowledge.faq_retriever import FAQRetriever

        return FAQRetriever(
            agent_id=agent_id,
            collection_name=knowledge_config.collection_name,
            top_k=knowledge_config.top_k,
        )

    elif knowledge_type == "vector":
        from app.services.knowledge.kb_retriever import KBRetriever

        return KBRetriever(
            collection_name=knowledge_config.collection_name,
            top_k=knowledge_config.top_k,
            rerank_enabled=knowledge_config.rerank_enabled,
        )

    elif knowledge_type == "product":
        # 商品检索复用现有 retriever
        from app.services.agent.retrieval.product import get_retriever

        return get_retriever(k=knowledge_config.top_k)

    elif knowledge_type == "graph":
        # 图谱检索（预留）
        logger.warning("图谱检索暂未实现", knowledge_type=knowledge_type)
        return None

    elif knowledge_type == "http_api":
        # 外部 API 检索（预留）
        logger.warning("HTTP API 检索暂未实现", knowledge_type=knowledge_type)
        return None

    else:
        raise ValueError(f"不支持的知识源类型: {knowledge_type}")
