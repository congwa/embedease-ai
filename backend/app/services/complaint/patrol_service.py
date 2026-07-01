"""客诉巡查服务

本文件的业务职责是让系统能主动扫描卡住的问题单，
并根据业务规则执行自动恢复、升级人工或告警留痕。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.complaint_patrol_event import ComplaintPatrolEvent
from app.models.complaint_ticket import ComplaintTicket
from app.repositories.complaint_patrol_event import ComplaintPatrolEventRepository
from app.repositories.complaint_task import ComplaintTaskRepository
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.schemas.complaint import ComplaintPatrolStatus, ComplaintStatus, ComplaintTaskStatus
from app.services.complaint.task_service import TaskService
from app.services.complaint.ticket_service import TicketService
from app.services.support.notification.dispatcher import notification_dispatcher

logger = get_logger("complaint.patrol")


@dataclass
class PatrolOutcome:
    """巡查处理结果。

    这个对象服务于 scheduler 任务，把巡查过程中发生的状态变化和队列刷新信息
    带回调度层，便于后续做 WebSocket 广播与执行统计。
    """

    ticket_id: str
    conversation_id: str
    ticket_status: str
    patrol_status: str
    event_type: str
    action_taken: str
    handoff_state: str


class PatrolService:
    """客诉巡查服务。

    第一阶段优先解决四类问题：
    1. 长时间 blocked 的 ticket 自动恢复
    2. 长时间 pending_review 的 ticket 升级人工
    3. 长时间 handoff_pending 的 ticket 触发提醒并留痕
    4. 返工次数过高的 ticket 直接升级人工，避免死循环
    """

    def __init__(self, session: AsyncSession):
        """初始化巡查服务。

        Args:
            session: 当前巡查任务使用的数据库会话。
        """
        self.session = session
        self.ticket_repo = ComplaintTicketRepository(session)
        self.task_repo = ComplaintTaskRepository(session)
        self.patrol_repo = ComplaintPatrolEventRepository(session)
        self.ticket_service = TicketService(session)
        self.task_service = TaskService(session)

    async def run_patrol(
        self,
        *,
        now: datetime | None = None,
        blocked_timeout_minutes: int = 20,
        pending_review_timeout_minutes: int = 15,
        handoff_pending_timeout_minutes: int = 10,
        handoff_reminder_cooldown_minutes: int = 30,
        rework_limit: int = 3,
    ) -> list[PatrolOutcome]:
        """执行一轮客诉巡查。

        这个方法是 scheduler 巡查任务的核心入口。它负责扫描候选 ticket，
        并按优先级执行返工死循环升级、阻塞恢复、审查超时升级和待人工提醒。
        """
        patrol_now = now or datetime.now()
        outcomes: list[PatrolOutcome] = []
        processed_ticket_ids: set[str] = set()

        candidates = await self._load_patrol_candidates(rework_limit=rework_limit)
        for ticket in candidates:
            if ticket.id in processed_ticket_ids:
                continue

            outcome = await self._inspect_ticket(
                ticket=ticket,
                now=patrol_now,
                blocked_timeout_minutes=blocked_timeout_minutes,
                pending_review_timeout_minutes=pending_review_timeout_minutes,
                handoff_pending_timeout_minutes=handoff_pending_timeout_minutes,
                handoff_reminder_cooldown_minutes=handoff_reminder_cooldown_minutes,
                rework_limit=rework_limit,
            )
            if outcome is None:
                continue

            processed_ticket_ids.add(ticket.id)
            outcomes.append(outcome)

        return outcomes

    async def _load_patrol_candidates(self, *, rework_limit: int) -> list[ComplaintTicket]:
        """加载本轮巡查候选问题单。

        这个方法把“状态超时类候选”与“返工死循环候选”合并成一批，供后续统一巡查。
        """
        status_candidates = await self.ticket_repo.list_primary_active_by_statuses(
            [
                ComplaintStatus.BLOCKED.value,
                ComplaintStatus.PENDING_REVIEW.value,
                ComplaintStatus.HANDOFF_PENDING.value,
                ComplaintStatus.REWORK_REQUIRED.value,
            ]
        )
        rework_candidates = await self.ticket_repo.list_primary_active_with_rework_at_least(rework_limit)

        ticket_map: dict[str, ComplaintTicket] = {}
        for ticket in status_candidates + rework_candidates:
            ticket_map[ticket.id] = ticket
        return sorted(ticket_map.values(), key=lambda item: item.updated_at)

    async def _inspect_ticket(
        self,
        *,
        ticket: ComplaintTicket,
        now: datetime,
        blocked_timeout_minutes: int,
        pending_review_timeout_minutes: int,
        handoff_pending_timeout_minutes: int,
        handoff_reminder_cooldown_minutes: int,
        rework_limit: int,
    ) -> PatrolOutcome | None:
        """对单张问题单执行巡查判断。

        这个方法按业务风险优先级依次判断是否需要升级人工、自动恢复或仅记录提醒。
        """
        stale_minutes = self._get_stale_minutes(ticket=ticket, now=now)

        if self._should_escalate_rework_loop(ticket=ticket, rework_limit=rework_limit):
            return await self._escalate_rework_loop(ticket=ticket)

        if (
            ticket.status == ComplaintStatus.BLOCKED.value
            and stale_minutes >= blocked_timeout_minutes
        ):
            return await self._recover_blocked_ticket(ticket=ticket)

        if (
            ticket.status == ComplaintStatus.PENDING_REVIEW.value
            and stale_minutes >= pending_review_timeout_minutes
        ):
            return await self._escalate_pending_review_timeout(ticket=ticket)

        if (
            ticket.status == ComplaintStatus.HANDOFF_PENDING.value
            and stale_minutes >= handoff_pending_timeout_minutes
        ):
            return await self._remind_stale_handoff_pending(
                ticket=ticket,
                now=now,
                cooldown_minutes=handoff_reminder_cooldown_minutes,
            )

        return None

    def _get_stale_minutes(self, *, ticket: ComplaintTicket, now: datetime) -> int:
        """计算问题单已停滞多久。

        这个方法服务于巡查规则判断，统一以 ticket 最近更新时间作为“最后一次真实推进时间”。
        """
        updated_at = ticket.updated_at or ticket.created_at or now
        return int((now - updated_at).total_seconds() // 60)

    def _should_escalate_rework_loop(
        self,
        *,
        ticket: ComplaintTicket,
        rework_limit: int,
    ) -> bool:
        """判断是否进入返工死循环。

        返工死循环一旦出现，继续自动执行往往只会重复犯错，因此应优先升级人工。
        """
        return (
            ticket.rework_count >= rework_limit
            and ticket.status not in {
                ComplaintStatus.HANDOFF_PENDING.value,
                ComplaintStatus.HANDED_OFF.value,
                ComplaintStatus.RESOLVED.value,
                ComplaintStatus.CLOSED.value,
            }
        )

    async def _recover_blocked_ticket(self, *, ticket: ComplaintTicket) -> PatrolOutcome:
        """自动恢复长时间阻塞的问题单。

        这个动作面向“流程被意外卡住但无需人工”的场景，把 ticket 恢复回 planned，
        并在最新阻塞任务上写入一次恢复痕迹。
        """
        latest_task = await self.task_repo.get_latest_by_ticket_id(ticket.id)
        if latest_task is not None and latest_task.status == ComplaintTaskStatus.BLOCKED.value:
            await self.task_service.resume_blocked_task(
                latest_task,
                reason="operations_patrol_agent 自动恢复阻塞任务",
            )

        recovered_ticket = await self.ticket_service.recover_from_blocked(
            ticket,
            summary="巡查发现长时间阻塞，已自动恢复为可继续规划状态",
        )
        event = await self._create_patrol_event(
            ticket=recovered_ticket,
            task_id=latest_task.id if latest_task is not None else None,
            event_type="blocked_timeout",
            patrol_status=ComplaintPatrolStatus.AUTO_RECOVERED.value,
            detected_reason="ticket 长时间处于 blocked 状态",
            action_taken="已恢复为 planned，并重启最新阻塞任务",
            result_payload={
                "latest_task_id": latest_task.id if latest_task is not None else None,
                "task_resumed": latest_task is not None,
            },
        )
        logger.info(
            "巡查自动恢复阻塞问题单",
            ticket_id=recovered_ticket.id,
            conversation_id=recovered_ticket.conversation_id,
            patrol_event_id=event.id,
        )
        return PatrolOutcome(
            ticket_id=recovered_ticket.id,
            conversation_id=recovered_ticket.conversation_id,
            ticket_status=recovered_ticket.status,
            patrol_status=event.status,
            event_type=event.event_type,
            action_taken=event.action_taken or "",
            handoff_state="ai",
        )

    async def _escalate_pending_review_timeout(self, *, ticket: ComplaintTicket) -> PatrolOutcome:
        """升级长时间待审查的问题单。

        这个动作面向 reviewer 没有及时收口的场景，直接把 ticket 升级到待人工接入，
        避免用户在高风险或不确定回复上无限等待。
        """
        latest_task = await self.task_repo.get_latest_by_ticket_id(ticket.id)
        if latest_task is not None and latest_task.status == ComplaintTaskStatus.WAITING_REVIEW.value:
            await self.task_service.block_task(latest_task, reason="pending_review_timeout")

        escalated_ticket = await self.ticket_service.mark_handoff_pending(
            ticket,
            handoff_reason="pending_review_timeout",
            handoff_summary={
                "source": "operations_patrol_agent",
                "reason": "审查等待超时，已升级人工兜底",
            },
        )
        await self.ticket_service.append_timeline_entry(
            escalated_ticket,
            event_type="patrol.review_timeout_escalated",
            summary="巡查发现待审查超时，已升级人工处理",
            extra={"task_id": latest_task.id if latest_task is not None else None},
        )
        event = await self._create_patrol_event(
            ticket=escalated_ticket,
            task_id=latest_task.id if latest_task is not None else None,
            event_type="pending_review_timeout",
            patrol_status=ComplaintPatrolStatus.ESCALATED.value,
            detected_reason="ticket 长时间处于 pending_review 状态",
            action_taken="已升级为 handoff_pending，由人工兜底",
            result_payload={
                "latest_task_id": latest_task.id if latest_task is not None else None,
                "task_blocked": latest_task is not None,
            },
        )
        logger.info(
            "巡查升级待审查超时问题单",
            ticket_id=escalated_ticket.id,
            conversation_id=escalated_ticket.conversation_id,
            patrol_event_id=event.id,
        )
        return PatrolOutcome(
            ticket_id=escalated_ticket.id,
            conversation_id=escalated_ticket.conversation_id,
            ticket_status=escalated_ticket.status,
            patrol_status=event.status,
            event_type=event.event_type,
            action_taken=event.action_taken or "",
            handoff_state="pending",
        )

    async def _escalate_rework_loop(self, *, ticket: ComplaintTicket) -> PatrolOutcome:
        """升级返工死循环问题单。

        当同一张问题单多次返工仍未收口时，继续自动执行会放大体验风险，
        应立即切到人工处理。
        """
        escalated_ticket = await self.ticket_service.mark_handoff_pending(
            ticket,
            handoff_reason="rework_loop",
            handoff_summary={
                "source": "operations_patrol_agent",
                "reason": "返工次数达到阈值，已停止自动处理并升级人工",
                "rework_count": ticket.rework_count,
            },
        )
        await self.ticket_service.append_timeline_entry(
            escalated_ticket,
            event_type="patrol.rework_loop_escalated",
            summary="巡查识别返工死循环，已升级人工处理",
            extra={"rework_count": ticket.rework_count},
        )
        event = await self._create_patrol_event(
            ticket=escalated_ticket,
            task_id=escalated_ticket.current_task_id,
            event_type="rework_loop",
            patrol_status=ComplaintPatrolStatus.ESCALATED.value,
            detected_reason="ticket 连续返工次数已达到阈值",
            action_taken="已升级为 handoff_pending，停止自动返工",
            result_payload={"rework_count": ticket.rework_count},
        )
        logger.info(
            "巡查升级返工死循环问题单",
            ticket_id=escalated_ticket.id,
            conversation_id=escalated_ticket.conversation_id,
            patrol_event_id=event.id,
        )
        return PatrolOutcome(
            ticket_id=escalated_ticket.id,
            conversation_id=escalated_ticket.conversation_id,
            ticket_status=escalated_ticket.status,
            patrol_status=event.status,
            event_type=event.event_type,
            action_taken=event.action_taken or "",
            handoff_state="pending",
        )

    async def _remind_stale_handoff_pending(
        self,
        *,
        ticket: ComplaintTicket,
        now: datetime,
        cooldown_minutes: int,
    ) -> PatrolOutcome | None:
        """对长时间待人工接入的问题单发出提醒并留痕。

        这个动作不重复推进状态，而是做提醒节流和巡查审计，避免客服队列长期无人认领。
        """
        cooldown_since = now - timedelta(minutes=cooldown_minutes)
        if await self.patrol_repo.has_recent_event(
            ticket_id=ticket.id,
            event_type="handoff_pending_timeout",
            since=cooldown_since,
        ):
            return None

        await self.ticket_service.append_timeline_entry(
            ticket,
            event_type="patrol.handoff_pending_alert",
            summary="巡查发现待人工接入超时，已发送提醒",
            extra={"cooldown_minutes": cooldown_minutes},
        )
        await self._notify_handoff_waiting(ticket=ticket, now=now)
        event = await self._create_patrol_event(
            ticket=ticket,
            task_id=ticket.current_task_id,
            event_type="handoff_pending_timeout",
            patrol_status=ComplaintPatrolStatus.ESCALATED.value,
            detected_reason="ticket 长时间处于 handoff_pending 状态",
            action_taken="已发送待接入提醒并记录巡查事件",
            result_payload={"cooldown_minutes": cooldown_minutes},
        )
        logger.info(
            "巡查记录待人工超时提醒",
            ticket_id=ticket.id,
            conversation_id=ticket.conversation_id,
            patrol_event_id=event.id,
        )
        return PatrolOutcome(
            ticket_id=ticket.id,
            conversation_id=ticket.conversation_id,
            ticket_status=ticket.status,
            patrol_status=event.status,
            event_type=event.event_type,
            action_taken=event.action_taken or "",
            handoff_state="pending",
        )

    async def _notify_handoff_waiting(
        self,
        *,
        ticket: ComplaintTicket,
        now: datetime,
    ) -> None:
        """发送待人工超时提醒。

        这个方法服务于 patrol 提醒链路。通知失败不影响巡查主流程，只写日志。
        """
        updated_at = ticket.updated_at or ticket.created_at or now
        wait_seconds = max(int((now - updated_at).total_seconds()), 0)
        try:
            await notification_dispatcher.notify_waiting_reminder(
                conversation_id=ticket.conversation_id,
                user_id=ticket.user_id,
                wait_seconds=wait_seconds,
            )
        except Exception as exc:
            logger.warning(
                "巡查发送待人工提醒失败",
                ticket_id=ticket.id,
                conversation_id=ticket.conversation_id,
                error=str(exc),
            )

    async def _create_patrol_event(
        self,
        *,
        ticket: ComplaintTicket,
        task_id: str | None,
        event_type: str,
        patrol_status: str,
        detected_reason: str,
        action_taken: str,
        result_payload: dict | None,
    ) -> ComplaintPatrolEvent:
        """创建巡查事件记录。

        这个方法服务于巡查审计，让后续工作台和运营分析可以解释自动恢复或升级动作。
        """
        event = ComplaintPatrolEvent(
            id=str(uuid.uuid4()),
            ticket_id=ticket.id,
            task_id=task_id,
            event_type=event_type,
            status=patrol_status,
            detected_reason=detected_reason,
            action_taken=action_taken,
            result_payload=result_payload,
            resolved_at=datetime.now(),
        )
        return await self.patrol_repo.create(event)
