"""客服会话状态组装服务

本文件的业务职责是把 Conversation、ComplaintTicket 和 ComplaintReview
组合成客服工作台与 WebSocket 都可复用的统一状态结构。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.models.conversation import Conversation
from app.repositories.complaint_review import ComplaintReviewRepository
from app.repositories.complaint_task import ComplaintTaskRepository
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.repositories.conversation import ConversationRepository
from app.schemas.support import (
    ConversationStateResponse,
    RecentTaskSummarySchema,
    ReviewSummarySchema,
    SecondaryIssueSchema,
    TicketDetailSchema,
    TicketSummarySchema,
)


class SupportStateService:
    """客服工作台状态组装服务。

    这个服务负责回答“当前会话的主问题单是谁、最近审查结果是什么、前端应该展示什么”。
    """

    def __init__(self, session: AsyncSession):
        """初始化客服状态组装服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.ticket_repo = ComplaintTicketRepository(session)
        self.task_repo = ComplaintTaskRepository(session)
        self.review_repo = ComplaintReviewRepository(session)

    async def get_conversation_state(
        self,
        conversation_id: str,
        *,
        unread_count: int = 0,
        peer_last_online_at: datetime | None = None,
    ) -> ConversationStateResponse | None:
        """获取客服工作台使用的完整会话状态。

        这个方法服务于 support API，让客服详情页一次拿全当前主问题单和最近 review 摘要。
        """
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            return None
        return await self.build_conversation_state(
            conversation,
            unread_count=unread_count,
            peer_last_online_at=peer_last_online_at,
        )

    async def build_conversation_state(
        self,
        conversation: Conversation,
        *,
        unread_count: int = 0,
        peer_last_online_at: datetime | None = None,
    ) -> ConversationStateResponse:
        """组装完整会话状态。

        这个方法把 conversation 快照、主问题单详情和最近 review 结果收敛成统一输出结构。
        """
        ticket = await self._get_current_ticket(conversation)
        review = await self._get_latest_review(ticket)
        recent_tasks = await self._list_recent_tasks(ticket)
        review_summary = self.build_review_summary(review)
        return ConversationStateResponse(
            conversation_id=conversation.id,
            conversation_mode=conversation.conversation_mode,
            handoff_state=conversation.handoff_state,
            handoff_operator=conversation.handoff_operator,
            handoff_reason=conversation.handoff_reason,
            handoff_at=conversation.handoff_at,
            last_notification_at=conversation.last_notification_at,
            current_ticket=self.build_ticket_summary(ticket),
            recent_tasks=[self.build_recent_task_summary(task) for task in recent_tasks],
            review_summary=review_summary,
            latest_review=review_summary,
            secondary_issues=self.build_secondary_issue_summaries(ticket),
            handoff_summary=dict(ticket.handoff_summary) if ticket and ticket.handoff_summary else None,
            user_online=conversation.user_online,
            peer_last_online_at=peer_last_online_at,
            unread_count=unread_count,
        )

    async def build_websocket_state_payload(
        self,
        conversation_id: str,
        *,
        unread_count: int = 0,
        peer_last_online_at: datetime | None = None,
    ) -> dict:
        """构建 WebSocket 使用的会话状态 payload。

        这个方法服务于 `system.connected` 和 `server.conversation_state` 推送，让客服端实时同步 ticket 状态。
        """
        conversation_state = await self.get_conversation_state(
            conversation_id,
            unread_count=unread_count,
            peer_last_online_at=peer_last_online_at,
        )
        if conversation_state is None:
            raise ValueError(f"构建客服会话状态失败，会话不存在: {conversation_id}")

        return {
            "conversation_mode": conversation_state.conversation_mode,
            "handoff_state": conversation_state.handoff_state,
            "operator": conversation_state.handoff_operator,
            "handoff_reason": conversation_state.handoff_reason,
            "user_online": conversation_state.user_online,
            "peer_last_online_at": (
                conversation_state.peer_last_online_at.isoformat()
                if conversation_state.peer_last_online_at
                else None
            ),
            "unread_count": conversation_state.unread_count,
            "current_ticket": (
                conversation_state.current_ticket.model_dump(mode="json")
                if conversation_state.current_ticket
                else None
            ),
            "review_summary": (
                conversation_state.review_summary.model_dump(mode="json")
                if conversation_state.review_summary
                else None
            ),
            "recent_tasks": [
                task.model_dump(mode="json") for task in conversation_state.recent_tasks
            ],
            "secondary_issues": [
                issue.model_dump(mode="json") for issue in conversation_state.secondary_issues
            ],
            "handoff_summary": conversation_state.handoff_summary,
        }

    async def get_active_ticket_detail(
        self,
        conversation_id: str,
    ) -> TicketDetailSchema | None:
        """获取会话当前主活动问题单详情。

        这个方法服务于客服工作台从会话跳进 ticket 视角时，直接拿到当前主处理对象。
        """
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            return None

        ticket = await self._get_current_ticket(conversation)
        if ticket is None:
            return None
        return await self.build_ticket_detail(ticket)

    async def get_ticket_detail(self, ticket_id: str) -> TicketDetailSchema | None:
        """获取单张问题单的完整详情。

        这个方法服务于客服工作台查看历史问题单和人工 resolve / reopen 操作后的详情刷新。
        """
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            return None
        return await self.build_ticket_detail(ticket)

    async def list_ticket_summaries_by_conversation(
        self,
        conversation_id: str,
    ) -> list[TicketSummarySchema]:
        """获取会话下全部问题单摘要。

        这个方法服务于工作台按会话查看历史 ticket 列表，而不必展开每张 ticket 的完整明细。
        """
        tickets = await self.ticket_repo.list_by_conversation_id(conversation_id)
        summaries: list[TicketSummarySchema] = []
        for ticket in tickets:
            summary = self.build_ticket_summary(ticket)
            if summary is not None:
                summaries.append(summary)
        return summaries

    async def build_ticket_detail(self, ticket: ComplaintTicket) -> TicketDetailSchema:
        """构建问题单完整详情。

        这个方法把 ticket、最近任务和最近审查结果收敛成客服工作台的单 ticket 视图合同。
        """
        latest_review = await self._get_latest_review(ticket)
        recent_tasks = await self._list_recent_tasks(ticket)
        return TicketDetailSchema(
            id=ticket.id,
            conversation_id=ticket.conversation_id,
            user_id=ticket.user_id,
            status=ticket.status,
            is_primary_active=ticket.is_primary_active,
            parent_ticket_id=ticket.parent_ticket_id,
            superseded_by_ticket_id=ticket.superseded_by_ticket_id,
            issue_fingerprint=ticket.issue_fingerprint,
            primary_issue_tag=ticket.primary_issue_tag,
            secondary_issue_tags=list(ticket.secondary_issue_tags or []),
            secondary_issues=self.build_secondary_issue_summaries(ticket),
            sentiment=ticket.sentiment,
            severity=ticket.severity,
            priority_level=ticket.priority_level,
            risk_level=ticket.risk_level,
            current_agent_tag=ticket.current_agent_tag,
            current_task_id=ticket.current_task_id,
            current_node_key=ticket.current_node_key,
            unresolved_turns=ticket.unresolved_turns,
            rework_count=ticket.rework_count,
            handoff_required=ticket.handoff_required,
            handoff_reason=ticket.handoff_reason,
            handoff_summary=dict(ticket.handoff_summary) if ticket.handoff_summary else None,
            resolved_summary=ticket.resolved_summary,
            slot_data=dict(ticket.slot_data or {}),
            timeline=list(ticket.timeline or []),
            version=ticket.version,
            latest_review=self.build_review_summary(latest_review),
            recent_tasks=[self.build_recent_task_summary(task) for task in recent_tasks],
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            resolved_at=ticket.resolved_at,
            closed_at=ticket.closed_at,
        )

    def build_ticket_summary(self, ticket: ComplaintTicket | None) -> TicketSummarySchema | None:
        """构建主问题单摘要。

        这个方法服务于客服列表和详情页，让前端不需要自行拼装问题单核心字段。
        """
        if ticket is None:
            return None

        return TicketSummarySchema(
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
            merged_from_latest_message=False,
            secondary_issue_detected=bool(ticket.secondary_issues),
            updated_at=ticket.updated_at,
        )

    def build_review_summary(self, review: ComplaintReview | None) -> ReviewSummarySchema | None:
        """构建最近一次审查摘要。

        这个方法服务于工作台提示“最近 review 是否通过、为什么被驳回”。
        """
        if review is None:
            return None

        return ReviewSummarySchema(
            status=review.status,
            score=review.score,
            risk_level=review.risk_level,
            reasons=list(review.reasons or []),
            suggested_next_agent=review.suggested_next_agent,
            created_at=review.created_at,
        )

    def build_recent_task_summary(self, task: ComplaintTask) -> RecentTaskSummarySchema:
        """构建最近任务摘要。

        这个方法服务于客服工作台的“处理链路”视图，让人工客服快速知道 AI 最近做了什么。
        """
        return RecentTaskSummarySchema(
            id=task.id,
            ticket_id=task.ticket_id,
            task_type=task.task_type,
            agent_tag=task.agent_tag,
            status=task.status,
            goal=task.goal,
            success_criteria=list(task.success_criteria or []),
            review_required=task.review_required,
            review_status=task.review_status,
            business_summary=self._build_task_business_summary(task),
            failure_reason=task.failure_reason,
            output_payload=task.output_payload,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
        )

    def build_secondary_issue_summaries(
        self,
        ticket: ComplaintTicket | None,
    ) -> list[SecondaryIssueSchema]:
        """构建次级诉求摘要列表。

        这个方法服务于客服接手时快速识别“主问题之外还夹带了哪些附带诉求”。
        """
        if ticket is None or not ticket.secondary_issues:
            return []

        summaries: list[SecondaryIssueSchema] = []
        for issue in ticket.secondary_issues:
            issue_payload = dict(issue or {})
            summaries.append(
                SecondaryIssueSchema(
                    issue_tag=str(issue_payload.pop("issue_tag", "secondary_issue")),
                    reason=issue_payload.pop("reason", None),
                    raw_message=issue_payload.pop("raw_message", None),
                    extra_data=issue_payload,
                )
            )
        return summaries

    async def _get_current_ticket(self, conversation: Conversation) -> ComplaintTicket | None:
        """获取当前主问题单。

        这个内部方法优先使用 conversation 快照中的 current_ticket_id，避免列表页和详情页查错问题单。
        """
        if conversation.current_ticket_id:
            ticket = await self.ticket_repo.get_by_id(conversation.current_ticket_id)
            if ticket is not None:
                return ticket
        return await self.ticket_repo.get_active_by_conversation_id(conversation.id)

    async def _get_latest_review(self, ticket: ComplaintTicket | None) -> ComplaintReview | None:
        """获取主问题单最近一次审查结果。

        这个内部方法只对当前主问题单查询 review，避免工作台拿到历史旧单的审查结果。
        """
        if ticket is None:
            return None
        return await self.review_repo.get_latest_by_ticket_id(ticket.id)

    async def _list_recent_tasks(self, ticket: ComplaintTicket | None) -> list[ComplaintTask]:
        """获取当前主问题单最近一组任务。

        这个内部方法只返回最新一段处理链路，避免工作台详情页一次加载过长历史。
        """
        if ticket is None:
            return []
        tasks = await self.task_repo.list_by_ticket_id(ticket.id)
        return tasks[-6:]

    def _build_task_business_summary(self, task: ComplaintTask) -> str | None:
        """提炼任务的业务摘要。

        这个内部方法把结构化 output_payload 压缩成客服可直接阅读的一句话说明。
        """
        payload = task.output_payload or {}

        if task.task_type == "triage" and payload.get("summary"):
            return str(payload["summary"])

        if task.task_type == "plan":
            assigned_agent = payload.get("assigned_agent_tag")
            reasoning = payload.get("reasoning")
            if assigned_agent and reasoning:
                return f"已分配给 {assigned_agent}：{reasoning}"
            if assigned_agent:
                return f"已分配给 {assigned_agent}"

        if task.task_type == "review":
            status = payload.get("status")
            reasons = payload.get("reasons") or []
            if status and reasons:
                return f"审查 {status}：{'；'.join(str(reason) for reason in reasons[:2])}"
            if status:
                return f"审查结果 {status}"

        if content := payload.get("content"):
            return str(content)[:120]

        if task.failure_reason:
            return task.failure_reason

        return task.goal
