"""客诉转人工编排服务

本文件的业务职责是把 complaint 语义下的 handoff 流程和底层 support handoff 状态机连起来，
确保 ticket 状态、会话模式、客服工作台推送三者始终一致。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_ticket import ComplaintTicket
from app.models.conversation import ConversationMode, HandoffState
from app.repositories.complaint_review import ComplaintReviewRepository
from app.repositories.complaint_task import ComplaintTaskRepository
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.repositories.conversation import ConversationRepository
from app.schemas.complaint import HandoffRequestResult
from app.schemas.websocket import WSAction, WSRole
from app.services.complaint.ticket_service import TicketService
from app.services.support.handoff import HandoffService
from app.services.support.state_service import SupportStateService
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager


class ComplaintHandoffService:
    """客诉 handoff 编排服务。

    这个服务对上暴露 complaint 语义的方法，对下复用 support handoff 状态机和工作台广播能力。
    """

    def __init__(self, session: AsyncSession):
        """初始化客诉 handoff 服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.task_repo = ComplaintTaskRepository(session)
        self.review_repo = ComplaintReviewRepository(session)
        self.ticket_repo = ComplaintTicketRepository(session)
        self.conversation_repo = ConversationRepository(session)
        self.ticket_service = TicketService(session)
        self.support_handoff_service = HandoffService(session)
        self.support_state_service = SupportStateService(session)

    async def request_handoff_for_ticket(
        self,
        ticket: ComplaintTicket,
        *,
        handoff_reason: str,
        handoff_summary: dict[str, Any] | None = None,
        requested_by: str = "complaint_system",
    ) -> HandoffRequestResult:
        """对指定问题单发起转人工请求。

        这个方法服务于 review 升级、用户明确要求人工和高风险场景的统一升级入口。
        """
        final_handoff_summary = await self._build_handoff_summary(
            ticket,
            handoff_reason=handoff_reason,
            requested_by=requested_by,
            extra_summary=handoff_summary,
        )
        if ticket.status not in {"handoff_pending", "handed_off"}:
            ticket = await self.ticket_service.mark_handoff_pending(
                ticket,
                handoff_reason=handoff_reason,
                handoff_summary=final_handoff_summary,
            )

        support_result = await self.support_handoff_service.request_handoff(
            ticket.conversation_id,
            reason=handoff_reason,
            requested_by=requested_by,
        )
        handoff_state = support_result.get("handoff_state") or HandoffState.PENDING.value

        await self._broadcast_ticket_update(ticket)
        await self._broadcast_conversation_state(ticket.conversation_id)
        await self._broadcast_support_queue_change(
            conversation_id=ticket.conversation_id,
            handoff_state=handoff_state,
            reason=handoff_reason,
            source="complaint_ticket_request_handoff",
        )

        return HandoffRequestResult(
            requested=bool(support_result.get("success")),
            conversation_id=ticket.conversation_id,
            ticket_id=ticket.id,
            handoff_reason=handoff_reason,
            handoff_summary=final_handoff_summary,
            conversation_mode=ConversationMode.PENDING.value,
            handoff_state=handoff_state,
        )

    async def request_handoff_for_conversation(
        self,
        *,
        conversation_id: str,
        handoff_reason: str,
        requested_by: str = "complaint_system",
        handoff_summary: dict[str, Any] | None = None,
    ) -> HandoffRequestResult:
        """对当前会话发起转人工请求。

        这个方法服务于用户在 WebSocket 里主动点“转人工”等不一定携带 ticket 上下文的入口。
        """
        ticket = await self.ticket_repo.get_active_by_conversation_id(conversation_id)
        if ticket is not None:
            return await self.request_handoff_for_ticket(
                ticket,
                handoff_reason=handoff_reason,
                handoff_summary=handoff_summary,
                requested_by=requested_by,
            )

        support_result = await self.support_handoff_service.request_handoff(
            conversation_id,
            reason=handoff_reason,
            requested_by=requested_by,
        )
        await self._broadcast_conversation_state(conversation_id)
        handoff_state = support_result.get("handoff_state") or HandoffState.PENDING.value
        await self._broadcast_support_queue_change(
            conversation_id=conversation_id,
            handoff_state=handoff_state,
            reason=handoff_reason,
            source="conversation_request_handoff",
        )
        return HandoffRequestResult(
            requested=bool(support_result.get("success")),
            conversation_id=conversation_id,
            ticket_id=None,
            handoff_reason=handoff_reason,
            handoff_summary=handoff_summary or {},
            conversation_mode=ConversationMode.PENDING.value,
            handoff_state=handoff_state,
        )

    async def accept_handoff(
        self,
        *,
        conversation_id: str,
        operator: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """接受待接入会话并切到人工处理中。

        这个方法服务于客服工作台点击接入，把 conversation 和当前 ticket 同步推进到人工处理中。
        """
        result = await self.support_handoff_service.start_handoff(
            conversation_id,
            operator=operator,
            reason=reason,
        )
        if not result.get("success"):
            return result

        ticket = await self._get_current_ticket(conversation_id)
        if ticket is not None and ticket.status == "handoff_pending":
            ticket = await self.ticket_service.mark_handed_off(ticket, operator=operator)
            await self._broadcast_ticket_update(ticket)

        await self._broadcast_conversation_state(conversation_id)
        await self._broadcast_support_queue_change(
            conversation_id=conversation_id,
            handoff_state=result.get("handoff_state") or HandoffState.HUMAN.value,
            reason=reason,
            source="accept_handoff",
        )
        return result

    async def finish_handoff(
        self,
        *,
        conversation_id: str,
        operator: str,
        summary: str = "",
    ) -> dict[str, Any]:
        """结束人工处理并同步 ticket 归档结果。

        第一阶段采用保守规则：
        - 有人工总结时，默认视为问题已解决
        - 无人工总结时，问题单交还 AI 继续推进
        """
        result = await self.support_handoff_service.end_handoff(
            conversation_id,
            operator=operator,
            summary=summary,
        )
        if not result.get("success"):
            return result

        ticket = await self._get_current_ticket(conversation_id)
        if ticket is not None:
            if summary:
                ticket = await self.ticket_service.mark_resolved(ticket, summary=summary)
            elif ticket.status == "handed_off":
                ticket = await self.ticket_service.resume_from_handoff(
                    ticket,
                    agent_tag="resolution_execution_agent",
                    node_key="resolution",
                )
            await self._broadcast_ticket_update(ticket)

        await self._broadcast_conversation_state(conversation_id)
        await self._broadcast_support_queue_change(
            conversation_id=conversation_id,
            handoff_state=result.get("handoff_state") or HandoffState.AI.value,
            reason=summary or None,
            source="finish_handoff",
        )
        return result

    async def transfer_handoff(
        self,
        *,
        conversation_id: str,
        operator: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """在人工处理中把会话转接给新的客服。

        这个方法服务于客服内部协同转单场景。客诉主 ticket 不改状态，
        只同步更新会话的 handoff_operator，并向工作台广播新的会话状态。
        """
        result = await self.support_handoff_service.transfer_handoff(
            conversation_id,
            operator=operator,
            reason=reason,
        )
        if not result.get("success"):
            return result

        await self._broadcast_conversation_state(conversation_id)
        await self._broadcast_support_queue_change(
            conversation_id=conversation_id,
            handoff_state=result.get("handoff_state") or HandoffState.HUMAN.value,
            reason=reason,
            source="transfer_handoff",
        )
        return result

    async def _get_current_ticket(self, conversation_id: str) -> ComplaintTicket | None:
        """获取当前会话的主问题单。

        这个内部方法优先走 conversation 快照，保证人工接入联动的是当前主问题单。
        """
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is not None and conversation.current_ticket_id:
            ticket = await self.ticket_repo.get_by_id(conversation.current_ticket_id)
            if ticket is not None:
                return ticket
        return await self.ticket_repo.get_active_by_conversation_id(conversation_id)

    async def _broadcast_ticket_update(self, ticket: ComplaintTicket) -> None:
        """广播 ticket 更新。

        这个内部方法服务于客服工作台和用户侧实时同步当前主问题单状态。
        """
        ticket_payload = self.ticket_service.build_stream_summary(ticket).model_dump(mode="json")
        message = build_server_message(
            action=WSAction.SERVER_TICKET_UPDATED,
            payload={"ticket": ticket_payload},
            conversation_id=ticket.conversation_id,
        )
        await ws_manager.broadcast_to_conversation(ticket.conversation_id, message)

    async def _broadcast_conversation_state(self, conversation_id: str) -> None:
        """广播完整会话状态。

        这个内部方法服务于 handoff 后工作台侧栏和详情页同步最新状态。
        """
        state_payload = await self.support_state_service.build_websocket_state_payload(conversation_id)
        message = build_server_message(
            action=WSAction.SERVER_CONVERSATION_STATE,
            payload=state_payload,
            conversation_id=conversation_id,
        )
        await ws_manager.broadcast_to_conversation(conversation_id, message)

    async def _broadcast_support_queue_change(
        self,
        *,
        conversation_id: str,
        handoff_state: str,
        reason: str | None,
        source: str,
    ) -> None:
        """广播客服全局队列变更信号。

        这个内部方法服务于客服列表页的跨会话刷新。即使目标会话不在当前监控集合内，
        任意一个在线客服连接也能收到“队列有变化”的信号并触发列表静默刷新。
        """
        message = build_server_message(
            action=WSAction.SERVER_SUPPORT_QUEUE_CHANGED,
            payload={
                "conversation_id": conversation_id,
                "handoff_state": handoff_state,
                "reason": reason,
                "source": source,
                "changed_at": datetime.now().isoformat(),
            },
            conversation_id=conversation_id,
        )
        await ws_manager.broadcast_to_role_global(WSRole.AGENT, message)

    async def _build_handoff_summary(
        self,
        ticket: ComplaintTicket,
        *,
        handoff_reason: str,
        requested_by: str,
        extra_summary: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """构建给人工客服使用的接手摘要。

        这个内部方法负责把当前主问题单的核心上下文压缩成 handoff_summary，
        让人工客服不用先翻完整聊天记录才能理解问题现状。
        """
        recent_tasks = await self.task_repo.list_by_ticket_id(ticket.id)
        latest_review = await self.review_repo.get_latest_by_ticket_id(ticket.id)

        summary: dict[str, Any] = {
            "ticket_id": ticket.id,
            "ticket_status": ticket.status,
            "primary_issue_tag": ticket.primary_issue_tag,
            "priority_level": ticket.priority_level,
            "risk_level": ticket.risk_level,
            "unresolved_turns": ticket.unresolved_turns,
            "current_agent_tag": ticket.current_agent_tag,
            "current_node_key": ticket.current_node_key,
            "slot_data": dict(ticket.slot_data or {}),
            "secondary_issues": list(ticket.secondary_issues or []),
            "timeline": list(ticket.timeline or [])[-5:],
            "recent_tasks": [
                self.support_state_service.build_recent_task_summary(task).model_dump(mode="json")
                for task in recent_tasks[-5:]
            ],
            "latest_review": (
                self.support_state_service.build_review_summary(latest_review).model_dump(mode="json")
                if latest_review is not None
                else None
            ),
            "requested_by": requested_by,
            "handoff_reason": handoff_reason,
        }

        if ticket.handoff_summary:
            summary.update(dict(ticket.handoff_summary))
        if extra_summary:
            summary.update(extra_summary)
        return summary
