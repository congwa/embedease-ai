"""客诉执行服务

本文件的业务职责是执行 planner 分派的岗位任务，生成候选回复、补齐槽位，
并把客诉处理能力统一收口到一处。

优先使用 LLM + complaint tools（faq_search / policy_search / case_sop_search /
handoff_create）执行；若 LLM 不可用或报错则自动降级到规则模板，保证主链路
在任何环境下都能产出候选回复。
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.complaint_ticket import ComplaintTicket
from app.schemas.agent import AgentConfig
from app.schemas.complaint import ComplaintTriageResult, ExecutorResult, PlannerDecision

ORDER_ID_PATTERN = re.compile(r"(?:订单号?|单号|order[\s:_-]*id)[：:\s#-]*([A-Za-z0-9-]{6,})", re.IGNORECASE)
PLAIN_ORDER_ID_PATTERN = re.compile(r"\b\d{6,20}\b")

logger = get_logger("complaint.executor")


class ExecutorService:
    """客诉 executor 服务。

    优先使用 LLM + complaint tools 执行岗位任务；若 LLM 不可用则降级为
    规则模板模式，保证主链路在任何情况下都能产出候选回复。
    """

    def __init__(self, session: AsyncSession, *, agent_config: AgentConfig | None = None):
        """初始化 executor 服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.agent_config = agent_config

    async def execute(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        planner_decision: PlannerDecision,
        last_user_message: str,
    ) -> ExecutorResult:
        """执行当前轮分派任务并输出标准化结果。

        优先走 LLM + tools 执行；LLM 不可用或报错时自动降级到规则模板。
        """
        collected_slots = self._extract_slots(last_user_message, existing_slots=ticket.slot_data or {})

        try:
            return await self._execute_with_llm(
                ticket=ticket,
                triage_result=triage_result,
                planner_decision=planner_decision,
                last_user_message=last_user_message,
                collected_slots=collected_slots,
            )
        except Exception as e:
            logger.warning(
                "LLM executor 执行失败，降级为规则模板",
                error=str(e),
                agent_tag=planner_decision.assigned_agent_tag,
            )
            return self._execute_with_rules(
                ticket=ticket,
                triage_result=triage_result,
                planner_decision=planner_decision,
                collected_slots=collected_slots,
            )

    async def _execute_with_llm(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        planner_decision: PlannerDecision,
        last_user_message: str,
        collected_slots: dict,
    ) -> ExecutorResult:
        """使用 LLM + complaint tools 执行岗位任务。

        对 LLM 进行工具绑定，执行 ReAct 工具调用循环（最多 5 轮），
        最终提取候选回复文本并封装为 ExecutorResult。
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

        from app.core.llm import get_chat_model

        llm = get_chat_model()
        tools = self._build_executor_tools()
        model: Any = llm.bind_tools(tools) if tools else llm

        system_prompt = self._build_executor_system_prompt(
            ticket=ticket,
            triage_result=triage_result,
            planner_decision=planner_decision,
            collected_slots=collected_slots,
        )
        if self.agent_config and self.agent_config.system_prompt:
            system_prompt += f"\n\n## 当前智能体要求\n{self.agent_config.system_prompt}"

        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=last_user_message),
        ]
        tool_map = {t.name: t for t in tools}
        final_content = ""

        for _ in range(5):
            response = await model.ainvoke(messages)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None)
            if not tool_calls:
                final_content = response.content or ""
                break

            for tc in tool_calls:
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    try:
                        result = await tool_fn.ainvoke(tc["args"])
                    except Exception as tool_err:
                        result = f"工具调用失败: {str(tool_err)}"
                else:
                    result = f"未知工具: {tc['name']}"
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        else:
            # 达到最大轮次，提取最近一条 AIMessage 内容
            for m in reversed(messages):
                if isinstance(m, AIMessage) and m.content:
                    final_content = m.content
                    break

        handoff_recommended = planner_decision.assigned_agent_tag == "handoff_orchestrator_agent"
        task_completed = bool(final_content) and not bool(triage_result.missing_slots)

        return ExecutorResult(
            content=final_content or "我已记录您的问题，将继续为您推进处理。",
            task_completed=task_completed,
            collected_slots=collected_slots,
            handoff_recommended=handoff_recommended,
            handoff_reason=planner_decision.reasoning if handoff_recommended else None,
            next_hint=planner_decision.next_node_key,
        )

    def _execute_with_rules(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        planner_decision: PlannerDecision,
        collected_slots: dict,
    ) -> ExecutorResult:
        """规则模板降级执行。

        当 LLM 不可用或报错时，回退到确定性模板策略，保证主链路稳定产出。
        """
        if planner_decision.assigned_agent_tag == "handoff_orchestrator_agent":
            return self._build_handoff_result(triage_result)

        if planner_decision.assigned_agent_tag == "emotion_deescalation_agent":
            return self._build_emotion_result(
                triage_result=triage_result,
                collected_slots=collected_slots,
            )

        if planner_decision.assigned_agent_tag == "case_intake_agent":
            return self._build_case_collect_result(
                triage_result=triage_result,
                collected_slots=collected_slots,
            )

        if planner_decision.assigned_agent_tag == "faq_policy_agent":
            return self._build_faq_result(
                ticket=ticket,
                triage_result=triage_result,
                collected_slots=collected_slots,
            )

        return self._build_resolution_result(
            ticket=ticket,
            triage_result=triage_result,
            collected_slots=collected_slots,
        )

    def _build_executor_system_prompt(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        planner_decision: PlannerDecision,
        collected_slots: dict,
    ) -> str:
        """构建 executor 角色的系统提示词。

        将工单上下文、triage 结果和 planner 决策格式化为结构化系统提示，
        引导 LLM 以正确岗位身份直接面向用户回复。
        """
        role_desc = {
            "emotion_deescalation_agent": "情绪安抚专员",
            "case_intake_agent": "信息收集专员",
            "faq_policy_agent": "规则解释专员",
            "resolution_execution_agent": "问题处理推进专员",
            "handoff_orchestrator_agent": "人工客服转接专员",
        }.get(planner_decision.assigned_agent_tag, "客诉处理专员")

        slot_summary = (
            "、".join(f"{k}={v}" for k, v in collected_slots.items())
            if collected_slots
            else "暂无"
        )
        missing_summary = (
            "、".join(triage_result.missing_slots) if triage_result.missing_slots else "无"
        )

        return f"""你是一名专业的{role_desc}，正在处理一个客诉工单，需要直接面向用户回复。

## 当前工单上下文
- 问题标签：{triage_result.primary_issue_tag or ticket.primary_issue_tag or "待识别"}
- 工单状态：{ticket.status}
- 情绪强度：{triage_result.emotional_intensity}（high/extreme 时需先安抚）
- 风险等级：{triage_result.risk_level}
- 问题摘要：{triage_result.summary}
- 已收集槽位：{slot_summary}
- 缺失槽位：{missing_summary}

## 本轮岗位任务
- 当前岗位：{role_desc}（{planner_decision.assigned_agent_tag}）
- 任务目标：{planner_decision.goal}
- 成功标准：{"；".join(planner_decision.success_criteria)}
- 规划依据：{planner_decision.reasoning}

## 回复要求
1. 用简洁、专业、有温度的中文直接回复用户，不要转述
2. 如有相关工具（FAQ、政策、SOP）可用，优先查询后再回复，确保信息准确
3. 一次说清楚，避免含糊其辞或套话
4. 不暴露内部系统状态（如 ticket ID、agent tag 等）
5. 回复长度控制在 2–4 句话，除非需要列举规则条文
6. 如需转人工，清楚告知用户原因和下一步操作"""

    def _build_executor_tools(self) -> list:
        """构建 executor 角色可用的 complaint 工具列表。

        为工具工厂创建最小化 AgentConfig，按 role_tag=executor 加载
        faq_search / policy_search / case_sop_search / handoff_create 工具。
        工具构建失败时返回空列表（LLM 仍可不带工具运行）。
        """
        try:
            from app.schemas.agent import AgentConfig

            config = self.agent_config or AgentConfig(
                agent_id="complaint_executor",
                name="客诉执行 Agent",
                type="custom",
                system_prompt="",
                role_tag="executor",
                knowledge_scope="complaint_faq",
            )

            from app.services.agent.tools.complaint.case_sop_search import (
                create_complaint_case_sop_search_tool,
            )
            from app.services.agent.tools.complaint.faq_search import (
                create_complaint_faq_search_tool,
            )
            from app.services.agent.tools.complaint.handoff_create import (
                create_handoff_create_tool,
            )
            from app.services.agent.tools.complaint.policy_search import (
                create_complaint_policy_search_tool,
            )

            tools = []
            for factory in [
                create_complaint_faq_search_tool,
                create_complaint_policy_search_tool,
                create_complaint_case_sop_search_tool,
                create_handoff_create_tool,
            ]:
                t = factory(config)
                if t is not None:
                    tools.append(t)
            return tools
        except Exception as e:
            logger.warning("构建 executor 工具失败，降级为无工具模式", error=str(e))
            return []

    def _extract_slots(
        self,
        user_message: str,
        *,
        existing_slots: dict,
    ) -> dict:
        """从当前消息里抽取基础业务槽位。

        这个内部方法先补订单号等高价值槽位，支持后续 resolution 与 handoff 摘要复用。
        """

        slot_data = dict(existing_slots)

        order_match = ORDER_ID_PATTERN.search(user_message)
        if order_match:
            slot_data["order_id"] = order_match.group(1)
        elif "order_id" not in slot_data:
            plain_order_match = PLAIN_ORDER_ID_PATTERN.search(user_message)
            if plain_order_match:
                slot_data["order_id"] = plain_order_match.group(0)

        if any(marker in user_message for marker in ("截图", "图片", "照片", "凭证")):
            slot_data["evidence_provided"] = True

        return slot_data

    def _build_handoff_result(self, triage_result: ComplaintTriageResult) -> ExecutorResult:
        """生成转人工确认结果。

        这个内部方法服务于高风险和明确人工请求场景，只负责生成接手确认与摘要提示。
        """

        return ExecutorResult(
            content=(
                "我已经为您记录当前问题，并会优先转给人工客服继续跟进。"
                "为了避免信息遗漏，客服接手时会直接看到您刚才的诉求摘要。"
            ),
            task_completed=True,
            collected_slots={},
            handoff_recommended=True,
            handoff_reason="planner 已判定当前场景需要人工介入",
            next_hint=f"人工接手原因：{triage_result.summary}",
        )

    def _build_emotion_result(
        self,
        *,
        triage_result: ComplaintTriageResult,
        collected_slots: dict,
    ) -> ExecutorResult:
        """生成情绪安抚型回复。

        这个内部方法服务于用户持续发泄和强情绪表达场景，先稳住情绪，再收口到处理动作。
        """

        order_id = collected_slots.get("order_id")
        if order_id:
            content = (
                f"非常抱歉这次给您带来这么差的体验，我已经先记录订单 {order_id} 的问题。"
                "我会按照您刚才提到的情况继续推进处理，并在需要补充信息时一次说清楚。"
            )
        else:
            content = (
                "非常抱歉这次让您这么不满意，我先完整记录您当前的诉求。"
                "为了尽快帮您推进，请补充订单号或相关凭证，这样我可以把问题准确挂到当前工单里继续处理。"
            )

        return ExecutorResult(
            content=content,
            task_completed=bool(order_id),
            collected_slots=collected_slots,
            handoff_recommended=False,
            handoff_reason=None,
            next_hint="若用户情绪仍持续升级，则下一轮优先评估是否转人工",
        )

    def _build_case_collect_result(
        self,
        *,
        triage_result: ComplaintTriageResult,
        collected_slots: dict,
    ) -> ExecutorResult:
        """生成信息补齐型回复。

        这个内部方法服务于资料不完整场景，要求一次说清楚当前缺什么信息。
        """

        remaining_slots = [slot for slot in triage_result.missing_slots if slot not in collected_slots]
        missing_labels = {
            "order_id": "订单号",
            "evidence": "截图或相关凭证",
            "issue_time": "问题发生时间",
            "contact_expectation": "您希望平台如何处理",
        }
        readable_slots = [missing_labels.get(slot, slot) for slot in remaining_slots]

        content = "我已经先记录了您的问题。"
        if readable_slots:
            content += f" 为了继续推进，请您补充：{'、'.join(readable_slots)}。"
        else:
            content += " 当前关键信息已经基本齐了，我会继续往处理环节推进。"

        return ExecutorResult(
            content=content,
            task_completed=not readable_slots,
            collected_slots=collected_slots,
            handoff_recommended=False,
            handoff_reason=None,
            next_hint="信息补齐后可转入 resolution 处理",
        )

    def _build_faq_result(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        collected_slots: dict,
    ) -> ExecutorResult:
        """生成规则解释型回复。

        这个内部方法服务于用户追问为什么、是否可以退款/赔付等政策说明场景。
        """

        order_id = collected_slots.get("order_id") or (ticket.slot_data or {}).get("order_id")
        content = (
            "我先把规则口径给您说清楚：平台会先核对订单事实、履约节点和相关凭证，"
            "再判断是否进入退款、补偿或申诉流程。"
        )
        if order_id:
            content += f" 您当前提供的订单号是 {order_id}，我会按这笔订单继续推进核查。"
        else:
            content += " 如果您方便，请补充订单号，这样我可以把规则解释和具体订单核查合并推进。"

        return ExecutorResult(
            content=content,
            task_completed=bool(order_id),
            collected_slots=collected_slots,
            handoff_recommended=False,
            handoff_reason=None,
            next_hint=f"当前主问题标签：{triage_result.primary_issue_tag}",
        )

    def _build_resolution_result(
        self,
        *,
        ticket: ComplaintTicket,
        triage_result: ComplaintTriageResult,
        collected_slots: dict,
    ) -> ExecutorResult:
        """生成常规处理推进回复。

        这个内部方法服务于信息已相对完整、可以给出明确下一步动作的场景。
        """

        order_id = collected_slots.get("order_id") or (ticket.slot_data or {}).get("order_id")
        if not order_id:
            return ExecutorResult(
                content="我已经理解您当前的问题，但继续处理前还需要订单号来对齐具体订单，请您补充后我继续推进。",
                task_completed=False,
                collected_slots=collected_slots,
                handoff_recommended=False,
                handoff_reason=None,
                next_hint="缺少订单号，下一轮应回到 case_collect",
            )

        content = (
            f"我已经按订单 {order_id} 记录并进入处理推进。"
            "接下来会先核对履约和服务记录，再根据核查结果给您明确的处理结论。"
        )
        if triage_result.risk_level == "medium":
            content += " 当前问题风险较高，我会优先保留完整记录，避免重复说明。"

        return ExecutorResult(
            content=content,
            task_completed=True,
            collected_slots=collected_slots,
            handoff_recommended=False,
            handoff_reason=None,
            next_hint="若用户继续追问，可复用当前 ticket 继续推进",
        )
