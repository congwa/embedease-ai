"""客诉绩效快照任务

本文件的业务职责是把 Agent 绩效统计接入 scheduler，
让系统能够按日自动生成质量与效率快照。
"""

from __future__ import annotations

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.scheduler.tasks.base import BaseTask, ScheduleType, TaskResult, TaskSchedule
from app.services.complaint.score_snapshot_service import ScoreSnapshotService

logger = get_logger("scheduler.tasks.complaint_score_snapshot")


class ComplaintScoreSnapshotTask(BaseTask):
    """客诉绩效快照任务。

    这个任务按固定窗口统计各岗位的 review 通过率、返工率、转人工率和平均处理时长，
    为后续运营分析提供可复用的快照数据。
    """

    name = "complaint_score_snapshot_task"
    description = "统计客诉 Agent 绩效快照"

    def __init__(
        self,
        *,
        cron_expression: str | None = None,
        run_on_start: bool | None = None,
    ):
        """初始化绩效快照任务。

        Args:
            cron_expression: 绩效统计任务的 cron 表达式。
            run_on_start: 调度器启动时是否立即跑一轮快照统计。
        """
        self.schedule = TaskSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression or settings.COMPLAINT_SCORE_SNAPSHOT_CRON,
            allow_concurrent=False,
            run_on_start=(
                settings.COMPLAINT_SCORE_SNAPSHOT_RUN_ON_START
                if run_on_start is None
                else run_on_start
            ),
        )
        self.enabled = settings.COMPLAINT_SCORE_SNAPSHOT_ENABLED

    async def run(self) -> TaskResult:
        """执行一轮绩效快照统计。

        这个方法服务于运营日报能力。若当前窗口没有有效任务，则返回成功但不写快照。
        """
        if not settings.COMPLAINT_SCORE_SNAPSHOT_ENABLED:
            return TaskResult.skipped("客诉绩效快照任务未启用")

        async with get_db_context() as session:
            service = ScoreSnapshotService(session)
            snapshots = await service.generate_snapshots(window_type="daily")

        logger.info(
            "客诉绩效快照任务执行完成",
            snapshot_count=len(snapshots),
            agent_tags=[snapshot.agent_tag for snapshot in snapshots],
        )
        return TaskResult.success(
            "客诉绩效快照统计完成",
            snapshot_count=len(snapshots),
            agent_tags=[snapshot.agent_tag for snapshot in snapshots],
        )
