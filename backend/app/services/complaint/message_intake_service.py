"""客诉消息接入服务

本文件的业务职责是把“用户刚发来的一条消息”接入投诉域主链路，
完成 ticket 归并、未解决轮次推进和前端投诉事件生成。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_ticket import ComplaintTicket
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.schemas.complaint import (
    ComplaintMessageIntakeResult,
    TicketResolutionDecision,
    TicketStreamSummary,
)
from app.services.complaint.ticket_merge_service import TicketMergeService
from app.services.complaint.ticket_service import TicketService


class ComplaintMessageIntakeService:
    """用户消息进入投诉域的接入服务。

    这个服务是 chat/router 和后续编排链路之间的桥梁，负责把每轮用户消息
    转成 ticket 决策和标准化前端事件。
    """

    def __init__(self, session: AsyncSession):
        """初始化客诉消息接入服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.ticket_repo = ComplaintTicketRepository(session)
        self.ticket_merge_service = TicketMergeService(session)
        self.ticket_service = TicketService(session)

    async def process_user_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        user_message: str,
        user_message_id: str,
    ) -> ComplaintMessageIntakeResult:
        """处理一条用户消息对应的投诉域状态推进。

        业务规则：
        - 先判断是创建首张 ticket、归并旧 ticket、记录次级问题还是拆单
        - 对归并和次级问题场景累加 unresolved_turns
        - 输出当前主问题单摘要和需要外发给前端的投诉事件
        """
        resolution = await self.ticket_merge_service.resolve_ticket_for_message(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=user_message,
        )

        ticket = await self.ticket_repo.get_by_id(resolution.ticket_id)
        if ticket is None:
            raise ValueError(f"投诉接入后未找到问题单: {resolution.ticket_id}")

        if resolution.decision in {
            TicketResolutionDecision.REUSE_ACTIVE_TICKET,
            TicketResolutionDecision.RECORD_SECONDARY_ISSUE,
        }:
            ticket = await self.ticket_service.increment_unresolved_turns(ticket)

        ticket_summary = self._build_ticket_summary(ticket, resolution.decision)
        return ComplaintMessageIntakeResult(
            resolution=resolution,
            ticket=ticket_summary,
            events=self._build_stream_events(
                ticket=ticket,
                ticket_summary=ticket_summary,
                decision=resolution.decision,
                reason=resolution.reason,
                user_message_id=user_message_id,
            ),
        )

    def _build_ticket_summary(
        self,
        ticket: ComplaintTicket,
        decision: TicketResolutionDecision,
    ) -> TicketStreamSummary:
        """构建当前主问题单的前端摘要。

        这个方法把数据库对象压缩成前端工作台和聊天页可以直接消费的状态摘要。
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

    def _build_stream_events(
        self,
        *,
        ticket: ComplaintTicket,
        ticket_summary: TicketStreamSummary,
        decision: TicketResolutionDecision,
        reason: str,
        user_message_id: str,
    ) -> list[dict[str, Any]]:
        """构建本轮用户消息需要外发的投诉域事件。

        Phase 1 先覆盖 ticket 创建、归并和次级问题识别三类入口事件，
        为前端和后续工作台联动提供统一协议。
        """
        ticket_payload = ticket_summary.model_dump(mode="json")

        if decision in {
            TicketResolutionDecision.CREATE_INITIAL_TICKET,
            TicketResolutionDecision.CREATE_NEW_TICKET,
        }:
            return [
                {
                    "type": "complaint.ticket.created",
                    "payload": {
                        "ticket": ticket_payload,
                    },
                }
            ]

        if decision == TicketResolutionDecision.REUSE_ACTIVE_TICKET:
            return [
                {
                    "type": "complaint.ticket.merged",
                    "payload": {
                        "ticket_id": ticket.id,
                        "merged_message_id": user_message_id,
                        "reason": reason,
                        "unresolved_turns": ticket.unresolved_turns,
                    },
                },
                {
                    "type": "complaint.ticket.updated",
                    "payload": {
                        "ticket": ticket_payload,
                    },
                },
            ]

        latest_secondary_issue = (ticket.secondary_issues or [{}])[-1]
        return [
            {
                "type": "complaint.secondary_issue.detected",
                "payload": {
                    "ticket_id": ticket.id,
                    "secondary_issue": latest_secondary_issue,
                },
            },
            {
                "type": "complaint.ticket.updated",
                "payload": {
                    "ticket": ticket_payload,
                },
            },
        ]
