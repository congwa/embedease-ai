"""FAQ 搜索工具

为 FAQ 类型 Agent 提供问答检索能力。
"""

from typing import TYPE_CHECKING, Any, Callable

from langchain_core.tools import tool

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig

logger = get_logger("tools.faq_search")


def create_faq_search_tool(config: "AgentConfig") -> Callable[..., Any] | None:
    """创建 FAQ 搜索工具

    Args:
        config: Agent 配置（包含知识源配置）

    Returns:
        FAQ 搜索工具函数，或 None（无知识源配置）
    """
    knowledge_config = config.knowledge_config
    if not knowledge_config:
        logger.warning("FAQ Agent 未配置知识源", agent_id=config.agent_id)
        return None

    # 从配置中获取检索参数
    top_k = knowledge_config.top_k
    collection_name = knowledge_config.collection_name or "faq_entries"

    @tool
    async def faq_search(query: str) -> str:
        """搜索 FAQ 知识库，获取相关问答

        Args:
            query: 用户问题或关键词

        Returns:
            相关 FAQ 条目的格式化结果
        """
        from app.services.knowledge.faq_retriever import FAQRetriever

        try:
            retriever = FAQRetriever(
                agent_id=config.agent_id,
                collection_name=collection_name,
                top_k=top_k,
            )

            results = await retriever.search(query)

            if not results:
                return "未找到相关的 FAQ 条目。建议用户换个问法或联系人工客服。"

            # 格式化输出
            output_parts = [f"找到 {len(results)} 条相关 FAQ：\n"]
            for i, item in enumerate(results, 1):
                output_parts.append(f"### FAQ {i}")
                output_parts.append(f"**问题**：{item['question']}")
                output_parts.append(f"**答案**：{item['answer']}")
                if item.get("category"):
                    output_parts.append(f"**分类**：{item['category']}")
                output_parts.append("")

            return "\n".join(output_parts)

        except Exception as e:
            logger.error("FAQ 搜索失败", error=str(e), query=query)
            return f"FAQ 搜索出错：{str(e)}"

    return faq_search
