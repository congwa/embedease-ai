"""客诉巡查任务

本文件的业务职责是把客诉巡查服务接入现有 scheduler，
让系统能够定时发现卡住 ticket 并触发自动恢复或人工升级。
"""

from __future__ import annotations

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.scheduler.tasks.base import BaseTask, ScheduleType, TaskResult, TaskSchedule
from app.schemas.websocket import WSAction, WSRole
from app.services.complaint.patrol_service import PatrolService
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager

logger = get_logger("scheduler.tasks.complaint_patrol")


class ComplaintPatrolTask(BaseTask):
    """客诉巡查任务。

    这个任务定时扫描长时间卡住的客诉问题单，并把自动恢复或升级人工的结果
    通过全局客服队列广播给工作台。
    """

    name = "complaint_patrol_task"
    description = "巡查卡住的客诉问题单并自动恢复或升级人工"

    def __init__(
        self,
        *,
        cron_expression: str | None = None,
        run_on_start: bool | None = None,
    ):
        """初始化客诉巡查任务。

        Args:
            cron_expression: 巡查任务的 cron 表达式。
            run_on_start: 调度器启动时是否立即跑一轮巡查。
        """
        self.schedule = TaskSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression or settings.COMPLAINT_PATROL_CRON,
            allow_concurrent=False,
            run_on_start=(
                settings.COMPLAINT_PATROL_RUN_ON_START
                if run_on_start is None
                else run_on_start
            ),
        )
        self.enabled = settings.COMPLAINT_PATROL_ENABLED

    async def run(self) -> TaskResult:
        """执行一轮客诉巡查。

        这个方法服务于后台 7x24 运维巡查能力。执行完成后会广播队列刷新，
        让在线客服页面及时看到被恢复或升级的会话。
        """
        if not settings.COMPLAINT_PATROL_ENABLED:
            return TaskResult.skipped("客诉巡查任务未启用")

        async with get_db_context() as session:
            service = PatrolService(session)
            outcomes = await service.run_patrol(
                blocked_timeout_minutes=settings.COMPLAINT_PATROL_BLOCKED_TIMEOUT_MINUTES,
                pending_review_timeout_minutes=settings.COMPLAINT_PATROL_PENDING_REVIEW_TIMEOUT_MINUTES,
                handoff_pending_timeout_minutes=settings.COMPLAINT_PATROL_HANDOFF_PENDING_TIMEOUT_MINUTES,
                handoff_reminder_cooldown_minutes=(
                    settings.COMPLAINT_PATROL_HANDOFF_REMINDER_COOLDOWN_MINUTES
                ),
                rework_limit=settings.COMPLAINT_PATROL_REWORK_LIMIT,
            )

        for outcome in outcomes:
            queue_msg = build_server_message(
                action=WSAction.SERVER_SUPPORT_QUEUE_CHANGED,
                payload={
                    "conversation_id": outcome.conversation_id,
                    "handoff_state": outcome.handoff_state,
                    "reason": outcome.event_type,
                    "source": "complaint_patrol_task",
                },
                conversation_id=outcome.conversation_id,
            )
            await ws_manager.broadcast_to_role_global(WSRole.AGENT, queue_msg)

        logger.info(
            "客诉巡查任务执行完成",
            outcome_count=len(outcomes),
            recovered_count=sum(1 for item in outcomes if item.patrol_status == "auto_recovered"),
            escalated_count=sum(1 for item in outcomes if item.patrol_status == "escalated"),
        )
        return TaskResult.success(
            "客诉巡查执行完成",
            outcome_count=len(outcomes),
            recovered_count=sum(1 for item in outcomes if item.patrol_status == "auto_recovered"),
            escalated_count=sum(1 for item in outcomes if item.patrol_status == "escalated"),
            conversations=[item.conversation_id for item in outcomes],
        )
