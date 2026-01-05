"""知识库搜索工具

为 KB 类型 Agent 提供内部知识库检索能力。
"""

from typing import TYPE_CHECKING, Any, Callable

from langchain_core.tools import tool

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig

logger = get_logger("tools.kb_search")


def create_kb_search_tool(config: "AgentConfig") -> Callable[..., Any] | None:
    """创建知识库搜索工具

    Args:
        config: Agent 配置（包含知识源配置）

    Returns:
        KB 搜索工具函数，或 None（无知识源配置）
    """
    knowledge_config = config.knowledge_config
    if not knowledge_config:
        logger.warning("KB Agent 未配置知识源", agent_id=config.agent_id)
        return None

    # 从配置中获取检索参数
    top_k = knowledge_config.top_k
    collection_name = knowledge_config.collection_name or "knowledge_base"
    rerank_enabled = knowledge_config.rerank_enabled

    @tool
    async def kb_search(query: str) -> str:
        """搜索内部知识库，获取相关文档

        Args:
            query: 查询问题或关键词

        Returns:
            相关文档的格式化结果
        """
        from app.services.knowledge.kb_retriever import KBRetriever

        try:
            retriever = KBRetriever(
                collection_name=collection_name,
                top_k=top_k,
                rerank_enabled=rerank_enabled,
            )

            results = await retriever.search(query)

            if not results:
                return "未找到相关的知识库文档。请尝试换个关键词或提供更多细节。"

            # 格式化输出
            output_parts = [f"找到 {len(results)} 条相关文档：\n"]
            for i, doc in enumerate(results, 1):
                output_parts.append(f"### 文档 {i}")
                output_parts.append(f"**内容**：{doc['content'][:500]}...")
                if doc.get("source"):
                    output_parts.append(f"**来源**：{doc['source']}")
                if doc.get("score"):
                    output_parts.append(f"**相关度**：{doc['score']:.2f}")
                output_parts.append("")

            return "\n".join(output_parts)

        except Exception as e:
            logger.error("知识库搜索失败", error=str(e), query=query)
            return f"知识库搜索出错：{str(e)}"

    return kb_search
