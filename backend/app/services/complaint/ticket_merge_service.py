"""问题单归并服务

本文件的业务职责是处理“当前消息应该归并到旧问题单、记录为次级问题，
还是创建新的问题单”这一核心业务判断。
第一阶段的强规则是：一个会话默认只有一个主活动问题单。
"""

from __future__ import annotations

import hashlib
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_ticket import ComplaintTicket
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.schemas.complaint import (
    ACTIVE_COMPLAINT_STATUSES,
    ActiveTicketResolution,
    ComplaintStatus,
    IssueContinuity,
    TicketResolutionDecision,
)
from app.services.complaint.ticket_service import TicketService


class TicketMergeService:
    """问题单归并与拆单服务。

    这个服务是 ticket 驱动主链路的入口，负责把用户持续发泄、补充信息、
    追问进度和引入次要诉求等场景统一映射到当前主活动问题单。
    """

    _SECONDARY_ISSUE_MARKERS = (
        "顺便",
        "另外",
        "还有个问题",
        "还有一个问题",
        "还有个诉求",
        "另外还想",
    )
    _NEW_TICKET_MARKERS = (
        "另一个订单",
        "新的问题",
        "新问题",
        "另一个问题",
        "另外一单",
    )

    def __init__(self, session: AsyncSession):
        """初始化问题单归并服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.ticket_repo = ComplaintTicketRepository(session)
        self.ticket_service = TicketService(session)

    async def get_or_create_active_ticket(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
    ) -> ActiveTicketResolution:
        """获取或创建当前主活动问题单。

        这个方法是主链路的统一入口：若当前没有活动问题单则新建，
        若已有活动问题单则按归并、次级问题或新问题规则返回决策结果。
        """
        return await self.resolve_ticket_for_message(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=user_message,
        )

    async def resolve_ticket_for_message(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
    ) -> ActiveTicketResolution:
        """判断当前消息应归属哪张问题单。

        业务规则：
        - 没有活动问题单时创建初始 ticket
        - 已关闭问题后出现新问题时创建新单
        - 默认优先归并到当前主活动问题单
        - 检测到次要问题时先挂 secondary issue
        - 只有高置信度新问题才拆成新单
        """
        active_ticket = await self.ticket_repo.get_active_by_conversation_id(conversation_id)

        if active_ticket is None:
            ticket = await self.create_initial_ticket(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
            )
            return ActiveTicketResolution(
                decision=TicketResolutionDecision.CREATE_INITIAL_TICKET,
                ticket_id=ticket.id,
                reason="当前会话没有主活动问题单，已创建首张问题单",
                issue_continuity=IssueContinuity.NEW_ISSUE,
                confidence=1.0,
            )

        if active_ticket.status not in {status.value for status in ACTIVE_COMPLAINT_STATUSES}:
            ticket = await self.create_initial_ticket(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                previous_ticket_id=active_ticket.id,
            )
            active_ticket.is_primary_active = False
            active_ticket.superseded_by_ticket_id = ticket.id
            await self.ticket_repo.update(active_ticket)
            return ActiveTicketResolution(
                decision=TicketResolutionDecision.CREATE_NEW_TICKET,
                ticket_id=ticket.id,
                previous_ticket_id=active_ticket.id,
                reason="旧问题单已结束，当前消息触发了新的主问题单",
                issue_continuity=IssueContinuity.NEW_ISSUE,
                confidence=0.95,
            )

        if self._looks_like_new_independent_issue(user_message):
            ticket = await self.create_initial_ticket(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                previous_ticket_id=active_ticket.id,
            )
            active_ticket.is_primary_active = False
            active_ticket.superseded_by_ticket_id = ticket.id
            await self.ticket_repo.update(active_ticket)
            return ActiveTicketResolution(
                decision=TicketResolutionDecision.CREATE_NEW_TICKET,
                ticket_id=ticket.id,
                previous_ticket_id=active_ticket.id,
                reason="当前消息高置信度指向新的独立问题，已拆出新问题单",
                issue_continuity=IssueContinuity.NEW_ISSUE,
                confidence=0.88,
            )

        if self._looks_like_secondary_issue(user_message):
            await self.attach_secondary_issue(active_ticket, user_message)
            return ActiveTicketResolution(
                decision=TicketResolutionDecision.RECORD_SECONDARY_ISSUE,
                ticket_id=active_ticket.id,
                previous_ticket_id=active_ticket.id,
                reason="当前消息在主问题之外引入了次级诉求，已记录 secondary issue",
                issue_continuity=IssueContinuity.UNCERTAIN,
                confidence=0.78,
            )

        return ActiveTicketResolution(
            decision=TicketResolutionDecision.REUSE_ACTIVE_TICKET,
            ticket_id=active_ticket.id,
            previous_ticket_id=active_ticket.id,
            reason="当前消息仍在围绕主活动问题单继续沟通，归并到现有问题单",
            issue_continuity=IssueContinuity.SAME_ISSUE,
            confidence=0.92,
        )

    async def create_initial_ticket(
        self,
        conversation_id: str,
        user_id: str,
        user_message: str,
        previous_ticket_id: str | None = None,
    ) -> ComplaintTicket:
        """创建初始或拆分后的主问题单。

        这个方法负责生成新问题单的基础字段，后续分类、规划和风险判断由其他服务继续补齐。
        """
        ticket = ComplaintTicket(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            user_id=user_id,
            status=ComplaintStatus.NEW.value,
            is_primary_active=True,
            parent_ticket_id=previous_ticket_id,
            issue_fingerprint=self.build_issue_fingerprint(user_message),
            unresolved_turns=0,
            rework_count=0,
            handoff_required=False,
            secondary_issue_tags=[],
            secondary_issues=[],
            slot_data={},
            timeline=[],
            version=1,
        )
        return await self.ticket_service.create_ticket(ticket)

    async def attach_secondary_issue(self, ticket: ComplaintTicket, user_message: str) -> ComplaintTicket:
        """将当前消息记录为主问题单下的次级诉求。

        第一阶段先保守记录 secondary issue，不自动拆出新单，留给 planner 或人工后续判断。
        """
        issues = list(ticket.secondary_issues or [])
        issues.append(
            {
                "issue_tag": "secondary_issue",
                "raw_message": user_message,
                "reason": "消息中出现了额外诉求，但暂不满足自动拆单条件",
            }
        )
        ticket.secondary_issues = issues
        tags = list(ticket.secondary_issue_tags or [])
        if "secondary_issue" not in tags:
            tags.append("secondary_issue")
        ticket.secondary_issue_tags = tags
        return await self.ticket_service.update_snapshot(ticket)

    def should_merge_into_current_ticket(self, ticket: ComplaintTicket, user_message: str) -> bool:
        """判断当前消息是否应继续归并到现有主问题单。

        这个方法服务于纯业务判定，不直接做数据库写入。
        """
        if ticket.status in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value}:
            return False
        return not self._looks_like_new_independent_issue(user_message)

    def build_issue_fingerprint(self, user_message: str) -> str:
        """为当前消息构建问题语义指纹。

        第一阶段使用轻量规则生成稳定哈希，后续可以升级成更复杂的语义特征。
        """
        normalized = re.sub(r"\s+", " ", user_message).strip().lower()
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    def _looks_like_secondary_issue(self, user_message: str) -> bool:
        """判断消息是否引入次级诉求。

        第一阶段使用明确的中文业务触发词做保守判断，避免误拆单。
        """
        normalized = user_message.strip()
        return any(marker in normalized for marker in self._SECONDARY_ISSUE_MARKERS)

    def _looks_like_new_independent_issue(self, user_message: str) -> bool:
        """判断消息是否高置信度触发新问题单。

        第一阶段门槛设高，只有出现显式新问题表述时才允许自动拆单。
        """
        normalized = user_message.strip()
        return any(marker in normalized for marker in self._NEW_TICKET_MARKERS)
