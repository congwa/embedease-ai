"""转人工摘要生成工具

为客诉 executor 角色提供转人工摘要生成能力。
当问题无法通过 AI 解决时，生成结构化的交接摘要对象，
供人工客服接手时快速了解情况。
"""

from typing import TYPE_CHECKING, Any, Callable

from langchain_core.tools import tool

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig

logger = get_logger("tools.complaint.handoff_create")


def create_handoff_create_tool(config: "AgentConfig") -> Callable[..., Any] | None:
    """创建转人工摘要生成工具

    Args:
        config: Agent 配置

    Returns:
        工具函数
    """

    @tool
    async def handoff_create(
        reason: str,
        issue_summary: str,
        user_emotion: str = "neutral",
        suggested_solution: str = "",
        urgency: str = "normal",
        collected_info: str = "",
    ) -> str:
        """生成结构化的转人工交接摘要，供人工客服接手时使用

        当问题需要升级到人工处理时调用此工具。工具会生成标准化的交接摘要，
        包含问题描述、用户情绪状态、已收集信息和建议处理方向。

        Args:
            reason: 转人工原因，如"用户多次拒绝 AI 解释方案""涉及金额超出 AI 授权范围"
            issue_summary: 问题简要描述，如"用户反映订单 #12345 延迟 3 天未发货"
            user_emotion: 用户情绪状态，如 angry/frustrated/neutral/calm
            suggested_solution: 建议的解决方案，如"建议赔偿延误险+优先处理补发"
            urgency: 紧急程度，normal/high/critical
            collected_info: 已收集的关键信息，如"订单号: 12345, 金额: 299元, 延迟天数: 3天"

        Returns:
            结构化的交接摘要 JSON 字符串，已格式化供人工客服阅读
        """
        import json

        handoff_summary = {
            "reason": reason,
            "issue_summary": issue_summary,
            "user_emotion": user_emotion,
            "urgency": urgency,
            "suggested_solution": suggested_solution,
            "collected_info": collected_info,
            "ai_agent": config.name,
        }

        # 格式化输出供 Agent 使用
        display = [
            "【转人工摘要已生成】",
            f"转人工原因：{reason}",
            f"问题描述：{issue_summary}",
            f"用户情绪：{user_emotion}",
            f"紧急程度：{urgency}",
        ]
        if collected_info:
            display.append(f"已收集信息：{collected_info}")
        if suggested_solution:
            display.append(f"建议方案：{suggested_solution}")
        display.append("")
        display.append(f"摘要数据：{json.dumps(handoff_summary, ensure_ascii=False)}")

        logger.info(
            "生成转人工摘要",
            agent_id=config.agent_id,
            reason=reason,
            urgency=urgency,
        )

        return "\n".join(display)

    return handoff_create
