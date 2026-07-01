"""客诉 FAQ 搜索工具

为客诉场景的 executor 角色提供 FAQ 问答检索能力。
与通用 FAQ 工具的区别：聚焦于客诉相关问答（退款政策、时效承诺、赔偿标准等），
按 knowledge_scope 限定检索范围。
"""

from typing import TYPE_CHECKING, Any, Callable

from langchain_core.tools import tool

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig

logger = get_logger("tools.complaint.faq_search")


def create_complaint_faq_search_tool(config: "AgentConfig") -> Callable[..., Any] | None:
    """创建客诉 FAQ 搜索工具

    Args:
        config: Agent 配置（knowledge_config 或 knowledge_scope 指定检索范围）

    Returns:
        工具函数，或 None（无知识源配置时降级为文本提示）
    """
    knowledge_config = config.knowledge_config
    knowledge_scope = config.knowledge_scope or "complaint_faq"

    top_k = knowledge_config.top_k if knowledge_config else 5
    collection_name = (
        knowledge_config.collection_name if knowledge_config else "faq_entries"
    )
    agent_id = config.agent_id

    @tool
    async def complaint_faq_search(query: str) -> str:
        """搜索客诉 FAQ 知识库，获取退款政策、时效承诺、赔偿标准等相关答案

        Args:
            query: 用户问题或关键词，如"延迟发货赔偿标准""退款到账时间"

        Returns:
            相关 FAQ 条目的格式化结果
        """
        from app.services.knowledge.faq_retriever import FAQRetriever

        try:
            retriever = FAQRetriever(
                agent_id=agent_id,
                collection_name=collection_name,
                top_k=top_k,
            )
            results = await retriever.search(query)

            if not results:
                return (
                    f'在客诉 FAQ 中未找到与"{query}"相关的条目。'
                    "请基于已知规则尽量回答，或说明需要进一步核实。"
                )

            output_parts = [f'找到 {len(results)} 条相关客诉 FAQ（知识范围：{knowledge_scope}）：\n']
            for i, item in enumerate(results, 1):
                output_parts.append(f"### FAQ {i}")
                output_parts.append(f"**问题**：{item['question']}")
                output_parts.append(f"**答案**：{item['answer']}")
                if item.get("category"):
                    output_parts.append(f"**分类**：{item['category']}")
                output_parts.append("")

            return "\n".join(output_parts)

        except Exception as e:
            logger.error("客诉 FAQ 搜索失败", error=str(e), query=query, scope=knowledge_scope)
            return f"FAQ 搜索出错：{str(e)}。请基于已知规则继续处理。"

    return complaint_faq_search
