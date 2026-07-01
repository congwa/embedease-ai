"""问题单服务

本文件的业务职责是维护问题单状态和会话快照之间的一致性，
确保工作台和用户聊天页可以随时看到当前主活动问题单的最新状态。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_ticket import ComplaintTicket
from app.models.conversation import Conversation, ConversationMode, HandoffState
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.repositories.conversation import ConversationRepository
from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintStatus,
    TicketResolutionDecision,
    TicketStreamSummary,
)
from app.services.complaint.state_machine import can_transition_ticket, require_transition


class TicketService:
    """问题单状态服务。

    这个服务负责推进 ticket 的业务状态，并同步更新 conversation 快照字段。
    """

    def __init__(self, session: AsyncSession):
        """初始化问题单状态服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.ticket_repo = ComplaintTicketRepository(session)
        self.conversation_repo = ConversationRepository(session)

    async def create_ticket(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """创建问题单并同步首个会话快照。

        这个方法用于首张 ticket 和拆单后的新 ticket 创建，确保 Conversation
        在第一时间就能看到新的主活动问题单。
        """
        created_ticket = await self.ticket_repo.create(ticket)
        conversation = await self.conversation_repo.get_by_id(created_ticket.conversation_id)
        if conversation is not None:
            self._apply_ticket_snapshot_to_conversation(conversation, created_ticket)
            await self.conversation_repo.update(conversation)
        return created_ticket

    async def update_snapshot(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """同步问题单快照到会话。

        这个方法让工作台和用户侧页面都能通过 Conversation 快照直接看到当前主问题单状态。
        """
        conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
        if conversation is not None:
            self._apply_ticket_snapshot_to_conversation(conversation, ticket)
            await self.conversation_repo.update(conversation)

        ticket.version += 1
        return await self.ticket_repo.update(ticket)

    async def update_ticket_snapshot(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """兼容旧调用名，继续同步问题单快照到会话。"""
        return await self.update_snapshot(ticket)

    async def update_classification(
        self,
        ticket: ComplaintTicket,
        *,
        primary_issue_tag: str | None = None,
        priority_level: str | None = None,
        risk_level: str | None = None,
        sentiment: str | None = None,
        severity: str | None = None,
    ) -> ComplaintTicket:
        """更新问题单分类快照。

        这个方法服务于 triage 阶段，把问题标签、优先级和风险等级同步到 ticket 与会话层。
        """
        ticket.primary_issue_tag = primary_issue_tag
        ticket.priority_level = priority_level
        ticket.risk_level = risk_level
        ticket.sentiment = sentiment
        ticket.severity = severity
        return await self.update_snapshot(ticket)

    async def increment_unresolved_turns(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """增加未解决轮次。

        当用户继续发泄、追问或补充信息时，应累加当前主问题单的未解决轮次。
        """
        ticket.unresolved_turns += 1
        return await self.update_snapshot(ticket)

    async def reset_unresolved_turns(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """重置未解决轮次。

        当问题已明确进入新阶段或已实质性推进时，可以重置未解决轮次。
        """
        ticket.unresolved_turns = 0
        return await self.update_snapshot(ticket)

    async def update_status(self, ticket: ComplaintTicket, status: ComplaintStatus | str) -> ComplaintTicket:
        """更新问题单状态。

        这个方法用于统一推进 new、planned、pending_review、handoff_pending 等业务状态。
        """
        next_status = status.value if isinstance(status, ComplaintStatus) else status
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=next_status,
            checker=can_transition_ticket,
        )
        ticket.status = next_status
        return await self.update_snapshot(ticket)

    async def set_current_agent(self, ticket: ComplaintTicket, agent_tag: str | None) -> ComplaintTicket:
        """更新当前责任岗位。

        当前责任岗位会同步显示在工作台列表和详情页中。
        """
        ticket.current_agent_tag = agent_tag
        return await self.update_snapshot(ticket)

    async def set_current_node(self, ticket: ComplaintTicket, node_key: str | None) -> ComplaintTicket:
        """更新当前流程节点。

        这个方法服务于编排链路，让工作台能够展示 ticket 当前卡在哪个业务节点。
        """
        ticket.current_node_key = node_key
        return await self.update_snapshot(ticket)

    async def set_current_task(self, ticket: ComplaintTicket, task_id: str | None) -> ComplaintTicket:
        """更新当前正在推进的任务。

        这个方法服务于工作台展示“当前问题单卡在哪一个任务上”。
        """
        ticket.current_task_id = task_id
        return await self.update_snapshot(ticket)

    async def merge_slot_data(self, ticket: ComplaintTicket, slot_data: dict | None) -> ComplaintTicket:
        """合并业务槽位数据。

        这个方法服务于 triage 和 executor 在多轮对话中持续补齐订单号、诉求、截图等槽位。
        """
        if not slot_data:
            return ticket
        current_slot_data = dict(ticket.slot_data or {})
        current_slot_data.update(slot_data)
        ticket.slot_data = current_slot_data
        return await self.update_snapshot(ticket)

    async def append_timeline_entry(
        self,
        ticket: ComplaintTicket,
        *,
        event_type: str,
        summary: str,
        extra: dict | None = None,
    ) -> ComplaintTicket:
        """追加 ticket 业务时间线。

        这个方法服务于后续工作台回溯，让客服能快速理解 AI 已经做过哪些关键动作。
        """
        timeline = list(ticket.timeline or [])
        timeline.append(
            {
                "event_type": event_type,
                "summary": summary,
                "extra": extra or {},
                "created_at": datetime.now().isoformat(),
            }
        )
        ticket.timeline = timeline
        return await self.update_snapshot(ticket)

    async def mark_triaged(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """标记问题单已完成 triage。

        这个方法服务于 front desk 完成分类之后，把 ticket 推进到可规划状态。
        """
        return await self.update_status(ticket, ComplaintStatus.TRIAGED)

    async def mark_planned(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """标记问题单已完成 planner 分派。

        这个方法服务于 planner 决定当前执行岗位之后，让工作台展示“已进入执行准备”。
        """
        return await self.update_status(ticket, ComplaintStatus.PLANNED)

    async def mark_in_progress(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """标记问题单进入执行中。

        这个方法服务于 executor 正式开始处理用户问题时的统一状态推进。
        """
        return await self.update_status(ticket, ComplaintStatus.IN_PROGRESS)

    async def mark_pending_review(self, ticket: ComplaintTicket) -> ComplaintTicket:
        """标记问题单进入待审查状态。

        这个动作表示 executor 已产出候选结果，当前等待 reviewer 决定是否可对外发送。
        """
        return await self.update_status(ticket, ComplaintStatus.PENDING_REVIEW)

    async def mark_rework_required(
        self,
        ticket: ComplaintTicket,
        *,
        block_reason: str | None = None,
    ) -> ComplaintTicket:
        """标记问题单需要返工。

        当 review 驳回后，当前主问题单需要回到 rework_required，以便 planner 重新分派。
        """
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=ComplaintStatus.REWORK_REQUIRED.value,
            checker=can_transition_ticket,
        )
        ticket.status = ComplaintStatus.REWORK_REQUIRED.value
        ticket.rework_count += 1
        if block_reason:
            conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
            if conversation is not None:
                conversation.block_reason = block_reason
                await self.conversation_repo.update(conversation)
        return await self.update_snapshot(ticket)

    async def mark_handoff_pending(
        self,
        ticket: ComplaintTicket,
        *,
        handoff_reason: str,
        handoff_summary: dict | None = None,
    ) -> ComplaintTicket:
        """标记问题单进入待人工接入。

        这个动作必须同时同步 ticket 状态、handoff 原因和 conversation 的等待人工模式。
        """
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=ComplaintStatus.HANDOFF_PENDING.value,
            checker=can_transition_ticket,
        )
        ticket.status = ComplaintStatus.HANDOFF_PENDING.value
        ticket.handoff_required = True
        ticket.handoff_reason = handoff_reason
        ticket.handoff_summary = handoff_summary

        conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
        if conversation is not None:
            conversation.conversation_mode = ConversationMode.PENDING.value
            conversation.handoff_state = HandoffState.PENDING.value
            conversation.handoff_reason = handoff_reason
            self._apply_ticket_snapshot_to_conversation(conversation, ticket)
            await self.conversation_repo.update(conversation)

        ticket.version += 1
        return await self.ticket_repo.update(ticket)

    async def mark_handed_off(
        self,
        ticket: ComplaintTicket,
        *,
        operator: str,
    ) -> ComplaintTicket:
        """标记问题单已被人工客服正式接手。

        这个动作服务于 pending -> human 的交接完成，让 ticket 和会话快照保持一致。
        """
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=ComplaintStatus.HANDED_OFF.value,
            checker=can_transition_ticket,
        )
        ticket.status = ComplaintStatus.HANDED_OFF.value
        ticket.current_agent_tag = operator
        return await self.update_snapshot(ticket)

    async def resume_from_handoff(
        self,
        ticket: ComplaintTicket,
        *,
        agent_tag: str | None = None,
        node_key: str | None = None,
    ) -> ComplaintTicket:
        """把问题单从人工接入态重新交还给 AI 继续推进。

        这个动作服务于人工结束后重新回到 AI 跟进的场景，确保 handoff 标记被清理。
        """
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=ComplaintStatus.IN_PROGRESS.value,
            checker=can_transition_ticket,
        )
        ticket.status = ComplaintStatus.IN_PROGRESS.value
        ticket.handoff_required = False
        ticket.handoff_reason = None
        ticket.handoff_summary = None
        if agent_tag is not None:
            ticket.current_agent_tag = agent_tag
        if node_key is not None:
            ticket.current_node_key = node_key
        return await self.update_snapshot(ticket)

    async def mark_blocked(
        self,
        ticket: ComplaintTicket,
        *,
        block_reason: str,
    ) -> ComplaintTicket:
        """标记问题单被阻塞。

        这个动作服务于 planner/executor 异常或信息断裂场景，避免系统继续假装成功推进。
        """
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=ComplaintStatus.BLOCKED.value,
            checker=can_transition_ticket,
        )
        ticket.status = ComplaintStatus.BLOCKED.value
        conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
        if conversation is not None:
            conversation.block_reason = block_reason
            self._apply_ticket_snapshot_to_conversation(conversation, ticket)
            await self.conversation_repo.update(conversation)
        ticket.version += 1
        return await self.ticket_repo.update(ticket)

    async def recover_from_blocked(
        self,
        ticket: ComplaintTicket,
        *,
        summary: str,
    ) -> ComplaintTicket:
        """把问题单从阻塞态恢复回可继续规划的状态。

        这个动作服务于巡查 Agent 的自动自愈。恢复后 ticket 会重新回到 planned，
        同时清理会话侧的阻塞原因，避免工作台一直显示过期卡点。
        """
        require_transition(
            entity_name="ticket",
            from_status=ticket.status,
            to_status=ComplaintStatus.PLANNED.value,
            checker=can_transition_ticket,
        )
        ticket.status = ComplaintStatus.PLANNED.value

        conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
        if conversation is not None:
            conversation.block_reason = None
            self._apply_ticket_snapshot_to_conversation(conversation, ticket)
            await self.conversation_repo.update(conversation)

        ticket.version += 1
        ticket = await self.ticket_repo.update(ticket)
        return await self.append_timeline_entry(
            ticket,
            event_type="patrol.auto_recovered",
            summary=summary,
            extra={
                "status": ticket.status,
                "current_agent_tag": ticket.current_agent_tag,
                "current_node_key": ticket.current_node_key,
            },
        )

    async def mark_resolved(self, ticket: ComplaintTicket, summary: str = "") -> ComplaintTicket:
        """标记问题单已解决。

        问题单解决后应退出主活动状态，但仍保留历史追踪能力。
        """
        if ticket.status != ComplaintStatus.RESOLVED.value:
            require_transition(
                entity_name="ticket",
                from_status=ticket.status,
                to_status=ComplaintStatus.RESOLVED.value,
                checker=can_transition_ticket,
            )
        ticket.status = ComplaintStatus.RESOLVED.value
        ticket.resolved_summary = summary or ticket.resolved_summary
        ticket.is_primary_active = False
        ticket.handoff_required = False
        ticket.resolved_at = datetime.now()
        return await self.update_snapshot(ticket)

    async def mark_closed(self, ticket: ComplaintTicket, summary: str = "") -> ComplaintTicket:
        """标记问题单已关闭。

        这个动作服务于人工或系统确认问题彻底结束后的最终归档。
        """
        if ticket.status != ComplaintStatus.CLOSED.value:
            require_transition(
                entity_name="ticket",
                from_status=ticket.status,
                to_status=ComplaintStatus.CLOSED.value,
                checker=can_transition_ticket,
            )
        ticket.status = ComplaintStatus.CLOSED.value
        ticket.resolved_summary = summary or ticket.resolved_summary
        ticket.is_primary_active = False
        ticket.handoff_required = False
        ticket.closed_at = datetime.now()
        return await self.update_snapshot(ticket)

    async def reopen_ticket(
        self,
        ticket: ComplaintTicket,
        *,
        reason: str = "",
        agent_tag: str | None = "resolution_execution_agent",
        node_key: str | None = "resolution",
    ) -> ComplaintTicket:
        """重开已结束问题单并交回主处理链路。

        这个动作服务于客服确认“问题并未真正解决”的场景，把已结束的问题单
        恢复成当前主活动 ticket，并把会话模式切回 AI 处理状态。
        """
        if ticket.status != ComplaintStatus.IN_PROGRESS.value:
            require_transition(
                entity_name="ticket",
                from_status=ticket.status,
                to_status=ComplaintStatus.IN_PROGRESS.value,
                checker=can_transition_ticket,
            )

        ticket.status = ComplaintStatus.IN_PROGRESS.value
        ticket.is_primary_active = True
        ticket.handoff_required = False
        ticket.handoff_reason = None
        ticket.handoff_summary = None
        ticket.resolved_at = None
        ticket.closed_at = None
        if agent_tag is not None:
            ticket.current_agent_tag = agent_tag
        if node_key is not None:
            ticket.current_node_key = node_key

        conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
        if conversation is not None:
            conversation.conversation_mode = ConversationMode.AI.value
            conversation.handoff_state = HandoffState.AI.value
            conversation.handoff_operator = None
            conversation.handoff_reason = None
            self._apply_ticket_snapshot_to_conversation(conversation, ticket)
            await self.conversation_repo.update(conversation)

        ticket.version += 1
        ticket = await self.ticket_repo.update(ticket)

        if reason:
            ticket = await self.append_timeline_entry(
                ticket,
                event_type="ticket.reopened",
                summary=reason,
                extra={
                    "agent_tag": ticket.current_agent_tag,
                    "node_key": ticket.current_node_key,
                },
            )
        return ticket

    async def sync_review_snapshot(
        self,
        ticket: ComplaintTicket,
        *,
        review_status: ComplaintReviewStatus | str,
        review_score: int | None = None,
    ) -> ComplaintTicket:
        """同步最近一次审查快照到会话。

        这个方法服务于工作台和用户侧“当前是否在 review、最近 review 得分如何”的展示。
        """
        conversation = await self.conversation_repo.get_by_id(ticket.conversation_id)
        if conversation is not None:
            conversation.review_status = (
                review_status.value if isinstance(review_status, ComplaintReviewStatus) else review_status
            )
            conversation.review_score = review_score
            await self.conversation_repo.update(conversation)
        return ticket

    def _apply_ticket_snapshot_to_conversation(
        self,
        conversation: Conversation,
        ticket: ComplaintTicket,
    ) -> None:
        """把主问题单快照写回会话。

        这个内部方法确保 conversation 始终可以直接回答“当前主活动问题单是谁、状态如何”。
        """
        conversation.current_ticket_id = ticket.id
        conversation.complaint_status = ticket.status
        conversation.primary_issue_tag = ticket.primary_issue_tag
        conversation.current_agent_tag = ticket.current_agent_tag
        conversation.current_node_key = ticket.current_node_key
        conversation.priority_level = ticket.priority_level
        conversation.risk_level = ticket.risk_level
        conversation.unresolved_turns = ticket.unresolved_turns
        conversation.secondary_issues = ticket.secondary_issues

    def build_stream_summary(
        self,
        ticket: ComplaintTicket,
        *,
        decision: TicketResolutionDecision | None = None,
    ) -> TicketStreamSummary:
        """构建标准化 ticket 摘要。

        这个方法服务于 SSE、WebSocket 和 Support API，保证它们看到的是同一套问题单快照。
        """
        return TicketStreamSummary(
            id=ticket.id,
            status=ticket.status,
            primary_issue_tag=ticket.primary_issue_tag,
            secondary_issue_tags=list(ticket.secondary_issue_tags or []),
            current_agent_tag=ticket.current_agent_tag,
            priority_level=ticket.priority_level,
            risk_level=ticket.risk_level,
            unresolved_turns=ticket.unresolved_turns,
            handoff_required=ticket.handoff_required,
            handoff_reason=ticket.handoff_reason,
            merged_from_latest_message=decision == TicketResolutionDecision.REUSE_ACTIVE_TICKET,
            secondary_issue_detected=decision == TicketResolutionDecision.RECORD_SECONDARY_ISSUE,
            updated_at=ticket.updated_at,
        )
