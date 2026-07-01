"""客诉案例 SOP / 处理流程查询工具

为客诉 executor 角色提供标准处理流程检索能力：
根据问题类型查找对应的处理 SOP、案例参考、话术模板。
"""

from typing import TYPE_CHECKING, Any, Callable

from langchain_core.tools import tool

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig

logger = get_logger("tools.complaint.case_sop_search")


def create_complaint_case_sop_search_tool(config: "AgentConfig") -> Callable[..., Any] | None:
    """创建客诉案例 SOP 查询工具

    Args:
        config: Agent 配置

    Returns:
        工具函数
    """
    knowledge_config = config.knowledge_config
    knowledge_scope = config.knowledge_scope or "complaint_sop"

    top_k = knowledge_config.top_k if knowledge_config else 5
    collection_name = (
        knowledge_config.collection_name if knowledge_config else "kb_documents"
    )
    agent_id = config.agent_id

    @tool
    async def complaint_case_sop_search(issue_type: str) -> str:
        """根据问题类型查找标准处理流程（SOP）、案例参考和话术模板

        Args:
            issue_type: 问题类型关键词，如"延迟发货""商品破损""退款未到账""虚假发货"

        Returns:
            对应的处理 SOP 步骤、话术参考和注意事项
        """
        try:
            from app.services.knowledge.kb_retriever import KBRetriever

            retriever = KBRetriever(
                agent_id=agent_id,
                collection_name=collection_name,
                top_k=top_k,
            )
            results = await retriever.search(f'处理流程 SOP {issue_type}')

            if not results:
                return (
                    f'未找到「{issue_type}」的标准处理流程。'
                    "请按以下通用步骤处理：\n"
                    "1. 确认问题详情（订单号、时间、金额）\n"
                    "2. 核实责任归属\n"
                    "3. 给出解决方案（补偿/补发/退款）\n"
                    "4. 确认用户接受并记录处理结果"
                )

            output_parts = [f'找到「{issue_type}」的处理流程参考（知识范围：{knowledge_scope}）：\n']
            for i, doc in enumerate(results, 1):
                output_parts.append(f"### SOP {i}")
                if doc.get("title"):
                    output_parts.append(f"**场景**：{doc['title']}")
                output_parts.append(f"**处理步骤**：{doc.get('content', doc.get('text', ''))}")
                if doc.get("source"):
                    output_parts.append(f"**来源**：{doc['source']}")
                output_parts.append("")

            return "\n".join(output_parts)

        except Exception as e:
            logger.error("SOP 查询失败", error=str(e), issue_type=issue_type, scope=knowledge_scope)
            return (
                f"SOP 查询出错：{str(e)}。\n"
                "请按通用客诉处理流程：核实问题 → 确认责任 → 给出方案 → 记录结果。"
            )

    return complaint_case_sop_search
