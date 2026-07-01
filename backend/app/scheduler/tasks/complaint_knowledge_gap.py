"""知识缺口分析任务

本文件的业务职责是定期分析 AgentScoreSnapshot 数据，识别高频驳回场景和知识盲区，
为知识库运营提供可操作的优化方向，避免同类问题反复导致 review 驳回或转人工。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.scheduler.tasks.base import BaseTask, ScheduleType, TaskResult, TaskSchedule

logger = get_logger("scheduler.tasks.complaint_knowledge_gap")


@dataclass
class KnowledgeGapReport:
    """知识缺口分析报告。

    这个数据对象服务于运营人员理解当前知识库的薄弱点，
    按 agent_tag 和 reason 维度给出优先级排序。
    """

    agent_tag: str
    top_reject_reasons: list[tuple[str, int]] = field(default_factory=list)
    top_handoff_reasons: list[tuple[str, int]] = field(default_factory=list)
    avg_pass_rate: float | None = None
    avg_rework_rate: float | None = None
    snapshot_count: int = 0
    is_critical: bool = False  # 通过率低于阈值时标记为关键缺口


class ComplaintKnowledgeGapTask(BaseTask):
    """知识缺口分析任务。

    这个任务通过聚合多个时间窗口内的 AgentScoreSnapshot，提炼出高频驳回原因和转人工原因，
    让知识库运营团队能快速识别"哪类问题 AI 总是答不好"并针对性补充知识。

    业务规则：
    - 每周运行一次（凌晨 3 点）
    - 取最近 N 条日粒度快照进行聚合（默认 7 条，覆盖一周数据）
    - 当某 agent_tag 的平均通过率低于阈值时，将该缺口标记为 critical 并发出更高级别告警
    - 分析结果以结构化日志输出，便于接入监控系统
    """

    name = "complaint_knowledge_gap_task"
    description = "分析客诉知识缺口，识别高频驳回场景"

    # 通过率低于此阈值标记为关键缺口
    CRITICAL_PASS_RATE_THRESHOLD = 0.60
    # 聚合最近几条日快照（默认 7 条 = 一周）
    RECENT_SNAPSHOT_LIMIT = 7

    def __init__(
        self,
        *,
        cron_expression: str | None = None,
        run_on_start: bool | None = None,
    ):
        """初始化知识缺口分析任务。

        Args:
            cron_expression: 任务 cron 表达式，默认每周一凌晨 3 点执行。
            run_on_start: 调度器启动时是否立即执行一次分析。
        """
        self.schedule = TaskSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression or getattr(
                settings, "COMPLAINT_KNOWLEDGE_GAP_CRON", "0 3 * * 1"
            ),
            allow_concurrent=False,
            run_on_start=(
                getattr(settings, "COMPLAINT_KNOWLEDGE_GAP_RUN_ON_START", False)
                if run_on_start is None
                else run_on_start
            ),
        )
        self.enabled = getattr(settings, "COMPLAINT_KNOWLEDGE_GAP_ENABLED", True)

    async def run(self) -> TaskResult:
        """执行一轮知识缺口分析。

        从数据库读取最近若干条 AgentScoreSnapshot，聚合高频驳回和转人工原因，
        输出结构化分析报告并以结构化日志形式推送到告警通道。
        """
        if not getattr(settings, "COMPLAINT_KNOWLEDGE_GAP_ENABLED", True):
            return TaskResult.skipped("知识缺口分析任务未启用")

        async with get_db_context() as session:
            from app.repositories.agent_score_snapshot import AgentScoreSnapshotRepository

            repo = AgentScoreSnapshotRepository(session)
            snapshots = await repo.list_by_window_type(
                "daily",
                limit=self.RECENT_SNAPSHOT_LIMIT * 10,  # 多取一些，再按 agent_tag 分组
            )

        if not snapshots:
            logger.info("知识缺口分析：暂无快照数据可分析")
            return TaskResult.skipped("暂无可用快照数据")

        reports = self._build_reports(snapshots)
        critical_count = sum(1 for r in reports if r.is_critical)

        for report in reports:
            self._emit_report_log(report)

        logger.info(
            "知识缺口分析完成",
            agent_count=len(reports),
            critical_count=critical_count,
            agent_tags=[r.agent_tag for r in reports],
        )

        return TaskResult.success(
            "知识缺口分析完成",
            agent_count=len(reports),
            critical_count=critical_count,
            reports=[
                {
                    "agent_tag": r.agent_tag,
                    "is_critical": r.is_critical,
                    "avg_pass_rate": r.avg_pass_rate,
                    "avg_rework_rate": r.avg_rework_rate,
                    "top_reject_reasons": r.top_reject_reasons[:3],
                    "top_handoff_reasons": r.top_handoff_reasons[:3],
                    "snapshot_count": r.snapshot_count,
                }
                for r in reports
            ],
        )

    def _build_reports(self, snapshots) -> list[KnowledgeGapReport]:
        """从快照列表构建按 agent_tag 分组的知识缺口报告。

        这个方法按 agent_tag 聚合多个快照的 payload，合并高频驳回/转人工原因，
        并计算该 agent 在分析窗口内的平均通过率和返工率。
        """
        from collections import defaultdict

        by_agent: dict[str, list] = defaultdict(list)
        for snapshot in snapshots:
            if snapshot.agent_tag:
                by_agent[snapshot.agent_tag].append(snapshot)

        reports: list[KnowledgeGapReport] = []
        for agent_tag, agent_snapshots in by_agent.items():
            # 取最近 RECENT_SNAPSHOT_LIMIT 条
            recent = sorted(
                agent_snapshots,
                key=lambda s: s.window_end,
                reverse=True,
            )[: self.RECENT_SNAPSHOT_LIMIT]

            reject_counter: Counter[str] = Counter()
            handoff_counter: Counter[str] = Counter()
            pass_rates: list[float] = []
            rework_rates: list[float] = []

            for snapshot in recent:
                payload = snapshot.payload or {}
                for reason, count in payload.get("reject_reasons_top", []):
                    reject_counter[reason] += count
                for reason, count in payload.get("handoff_reasons_top", []):
                    handoff_counter[reason] += count
                if snapshot.pass_rate is not None:
                    pass_rates.append(snapshot.pass_rate)
                if snapshot.rework_rate is not None:
                    rework_rates.append(snapshot.rework_rate)

            avg_pass_rate = sum(pass_rates) / len(pass_rates) if pass_rates else None

            report = KnowledgeGapReport(
                agent_tag=agent_tag,
                top_reject_reasons=reject_counter.most_common(5),
                top_handoff_reasons=handoff_counter.most_common(5),
                avg_pass_rate=avg_pass_rate,
                avg_rework_rate=sum(rework_rates) / len(rework_rates) if rework_rates else None,
                snapshot_count=len(recent),
                is_critical=(
                    avg_pass_rate is not None
                    and avg_pass_rate < self.CRITICAL_PASS_RATE_THRESHOLD
                ),
            )
            reports.append(report)

        # 按通过率升序排列（最差的排最前面，优先关注）
        reports.sort(key=lambda r: r.avg_pass_rate if r.avg_pass_rate is not None else 1.0)
        return reports

    def _emit_report_log(self, report: KnowledgeGapReport) -> None:
        """输出结构化的知识缺口报告日志。

        这个方法把分析结果以可被监控系统解析的格式输出，
        critical 级别的缺口使用 warning 日志，其余使用 info 日志。
        """
        log_fn = logger.warning if report.is_critical else logger.info
        log_fn(
            "知识缺口分析报告",
            agent_tag=report.agent_tag,
            is_critical=report.is_critical,
            avg_pass_rate=round(report.avg_pass_rate, 3) if report.avg_pass_rate is not None else None,
            avg_rework_rate=round(report.avg_rework_rate, 3) if report.avg_rework_rate is not None else None,
            snapshot_count=report.snapshot_count,
            top_reject_reasons=report.top_reject_reasons[:3],
            top_handoff_reasons=report.top_handoff_reasons[:3],
        )
