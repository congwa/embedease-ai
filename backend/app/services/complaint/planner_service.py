"""客诉规划服务

本文件的业务职责是根据当前 ticket 快照和 triage 结果，
决定这轮消息应该由哪个岗位接手、目标是什么以及是否需要转人工。

优先使用 LLM 结构化输出进行智能规划；若 LLM 不可用或输出无效，
则自动降级为确定性规则引擎，保证规划结果在任意环境下均有输出。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import ComplaintTriageResult, PlannerDecision

logger = get_logger("complaint.planner")

# 可分派的岗位说明，用于在 LLM 提示词中描述各选项含义
_AGENT_OPTIONS = """
可选岗位（assigned_agent_tag）：
- handoff_orchestrator_agent：需要升级到人工客服（高风险、用户明确要求、多次返工）
- emotion_deescalation_agent：用户情绪激动，需要先安抚再处理
- case_intake_agent：关键信息不足，需要向用户补充收集
- faq_policy_agent：用户询问规则/政策/退款条件，需要解释说明
- resolution_execution_agent：信息充足，直接推进问题解决
"""


class PlannerService:
    """客诉 planner 服务。

    优先使用 LLM 结构化输出进行智能规划；LLM 不可用时降级为规则引擎，
    保证规划结果在任意环境下均有输出。
    """

    def __init__(self, session: AsyncSession):
        """初始化 planner 服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session

    async def plan(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        last_user_message: str,
    ) -> PlannerDecision:
        """根据当前 ticket 和 triage 结果生成本轮执行计划。

        优先走 LLM 结构化输出；LLM 不可用或输出无效时降级为规则引擎。
        """
        try:
            return await self._plan_with_llm(
                ticket=ticket,
                triage_result=triage_result,
                last_user_message=last_user_message,
            )
        except Exception as e:
            logger.warning(
                "LLM planner 失败，降级为规则引擎",
                error=str(e),
            )
            return self._plan_with_rules(
                ticket=ticket,
                triage_result=triage_result,
                last_user_message=last_user_message,
            )

    async def _plan_with_llm(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        last_user_message: str,
    ) -> PlannerDecision:
        """使用 LLM 结构化输出生成规划决策。

        通过 `with_structured_output(PlannerDecision)` 强制 LLM 返回合法的
        PlannerDecision 对象，省去手动解析步骤。
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from app.core.llm import get_chat_model

        llm = get_chat_model()
        structured_llm = llm.with_structured_output(PlannerDecision)

        slot_summary = (
            "、".join(f"{k}={v}" for k, v in (ticket.slot_data or {}).items())
            or "暂无"
        )
        missing_summary = (
            "、".join(triage_result.missing_slots) if triage_result.missing_slots else "无"
        )

        system_prompt = f"""你是一名客诉处理规划师，负责为当前轮对话选择最合适的处理岗位。

## 当前工单状态
- 问题标签：{triage_result.primary_issue_tag or ticket.primary_issue_tag or "未知"}
- 情绪强度：{triage_result.emotional_intensity}
- 风险等级：{triage_result.risk_level}
- 是否请求人工：{triage_result.requested_human}
- 问题摘要：{triage_result.summary}
- 已收集槽位：{slot_summary}
- 缺失槽位：{missing_summary}
- 当前返工次数：{ticket.rework_count}
- 强制转人工标记：{ticket.handoff_required}

{_AGENT_OPTIONS}

## 规划规则（按优先级）
1. 若 handoff_required=True 或 requested_human=True 或 risk_level=high，必须选 handoff_orchestrator_agent
2. 若 emotional_intensity 为 high 或 extreme，优先选 emotion_deescalation_agent
3. 若缺失槽位不为空，优先选 case_intake_agent
4. 若用户消息涉及政策/规则/退款原因询问，选 faq_policy_agent
5. 其他情况选 resolution_execution_agent

请根据以上信息输出规划决策，task_type 与 assigned_agent_tag 保持一致。"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_user_message),
        ]

        result = await structured_llm.ainvoke(messages)

        if not isinstance(result, PlannerDecision):
            raise ValueError(f"LLM 输出无效，类型为 {type(result)}")

        logger.info(
            "LLM planner 完成规划",
            assigned_agent=result.assigned_agent_tag,
            task_type=result.task_type,
            should_handoff=result.should_handoff,
        )
        return result

    def _plan_with_rules(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        last_user_message: str,
    ) -> PlannerDecision:
        """规则引擎降级规划。

        按优先级匹配确定性规则，保证任意情况下都能产出合法的 PlannerDecision。
        规划优先级：高风险/请求人工 > 情绪失控 > 信息不足 > 规则解释 > 常规推进。
        """
        normalized_message = last_user_message.lower()

        if triage_result.requested_human or triage_result.risk_level == "high" or ticket.handoff_required:
            return PlannerDecision(
                assigned_agent_tag="handoff_orchestrator_agent",
                task_type="handoff",
                goal="生成接手摘要并把当前问题升级到人工客服",
                success_criteria=["handoff_reason 已记录", "人工客服可直接接手"],
                should_handoff=True,
                next_node_key="handoff",
                reasoning="当前消息触发了高风险或明确人工接入规则",
            )

        if triage_result.emotional_intensity in {"high", "extreme"}:
            return PlannerDecision(
                assigned_agent_tag="emotion_deescalation_agent",
                task_type="emotion",
                goal="先稳定用户情绪，再把对话拉回到可处理的信息收集或处理推进上",
                success_criteria=["完成情绪安抚", "下一步处理要求表达清楚"],
                should_handoff=False,
                next_node_key="emotion",
                reasoning="用户情绪强度较高，需要先做情绪降温",
            )

        if triage_result.missing_slots:
            return PlannerDecision(
                assigned_agent_tag="case_intake_agent",
                task_type="case_collect",
                goal="补齐当前问题继续推进所需的关键信息",
                success_criteria=[f"{slot} 已补齐" for slot in triage_result.missing_slots],
                should_handoff=False,
                next_node_key="case_collect",
                reasoning="当前问题继续处理仍缺少关键业务槽位",
            )

        policy_markers = ("规则", "政策", "为什么", "凭什么", "能不能", "可以吗", "退款", "赔付")
        if any(marker in last_user_message for marker in policy_markers) or "policy" in normalized_message:
            return PlannerDecision(
                assigned_agent_tag="faq_policy_agent",
                task_type="faq",
                goal="给出清晰一致的规则解释，并说明下一步处理路径",
                success_criteria=["规则说明清晰", "用户知道下一步怎么做"],
                should_handoff=False,
                next_node_key="faq",
                reasoning="当前问题更像规则解释或政策答疑场景",
            )

        return PlannerDecision(
            assigned_agent_tag="resolution_execution_agent",
            task_type="resolution",
            goal="基于现有信息推进问题处理或给出明确下一步动作",
            success_criteria=["回复给出明确动作", "用户知道当前问题在如何推进"],
            should_handoff=False,
            next_node_key="resolution",
            reasoning="当前信息已经足够进入常规处理推进阶段",
        )
