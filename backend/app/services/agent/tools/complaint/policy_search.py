"""客诉规则/政策查询工具

为客诉 executor 角色提供规则解释能力：平台规则、退款政策、
赔偿标准、服务承诺等结构化政策文档的检索。
"""

from typing import TYPE_CHECKING, Any, Callable

from langchain_core.tools import tool

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig

logger = get_logger("tools.complaint.policy_search")


def create_complaint_policy_search_tool(config: "AgentConfig") -> Callable[..., Any] | None:
    """创建客诉规则/政策查询工具

    Args:
        config: Agent 配置

    Returns:
        工具函数，或 None（无知识源时降级）
    """
    knowledge_config = config.knowledge_config
    knowledge_scope = config.knowledge_scope or "complaint_policy"

    top_k = knowledge_config.top_k if knowledge_config else 5
    collection_name = (
        knowledge_config.collection_name if knowledge_config else "kb_documents"
    )
    agent_id = config.agent_id

    @tool
    async def complaint_policy_search(query: str) -> str:
        """查询平台规则和政策文档，包括退款规则、赔偿标准、服务承诺、时效规定等

        Args:
            query: 规则关键词，如"延迟发货赔偿规则""七天无理由退货政策""运费险理赔条件"

        Returns:
            相关政策文档片段，带出处说明
        """
        try:
            from app.services.knowledge.kb_retriever import KBRetriever

            retriever = KBRetriever(
                agent_id=agent_id,
                collection_name=collection_name,
                top_k=top_k,
            )
            results = await retriever.search(query)

            if not results:
                return (
                    f'在政策文档中未找到与"{query}"直接匹配的规则条文。'
                    '请基于通用商业惯例处理，并在回复中注明「以实际平台政策为准」。'
                )

            output_parts = [f'找到 {len(results)} 条相关政策条文（知识范围：{knowledge_scope}）：\n']
            for i, doc in enumerate(results, 1):
                output_parts.append(f"### 政策 {i}")
                if doc.get("title"):
                    output_parts.append(f"**标题**：{doc['title']}")
                output_parts.append(f"**内容**：{doc.get('content', doc.get('text', ''))}")
                if doc.get("source"):
                    output_parts.append(f"**来源**：{doc['source']}")
                output_parts.append("")

            return "\n".join(output_parts)

        except Exception as e:
            logger.error("政策查询失败", error=str(e), query=query, scope=knowledge_scope)
            return f"政策查询出错：{str(e)}。请基于通用规则继续处理，并注明需核实具体政策。"

    return complaint_policy_search
