"""客诉绩效快照服务

本文件的业务职责是把 task/review 的执行结果聚合成 Agent 绩效快照，
为后续日报、排行榜和知识运营提供稳定的数据基座。
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_score_snapshot import AgentScoreSnapshot
from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.repositories.agent_score_snapshot import AgentScoreSnapshotRepository
from app.schemas.complaint import ComplaintReviewStatus


@dataclass
class ScoreWindow:
    """绩效统计窗口。

    这个对象服务于快照任务，明确当前统计是覆盖哪一段业务时间范围。
    """

    window_type: str
    window_start: datetime
    window_end: datetime


class ScoreSnapshotService:
    """客诉绩效快照服务。

    第一阶段优先把执行岗位的通过率、返工率、转人工率、平均审查分和处理时长统计出来，
    让系统具备持续优化的运营抓手。
    """

    def __init__(self, session: AsyncSession):
        """初始化绩效快照服务。

        Args:
            session: 当前后台统计任务使用的数据库会话。
        """
        self.session = session
        self.snapshot_repo = AgentScoreSnapshotRepository(session)

    def build_window(
        self,
        *,
        window_type: str = "daily",
        now: datetime | None = None,
    ) -> ScoreWindow:
        """构造统计时间窗口。

        当前先支持 daily 和 hourly 两类窗口，满足日常巡检和手动验证场景。
        """
        current_time = now or datetime.now()
        if window_type == "hourly":
            window_end = current_time.replace(minute=0, second=0, microsecond=0)
            return ScoreWindow(
                window_type=window_type,
                window_start=window_end - timedelta(hours=1),
                window_end=window_end,
            )

        window_end = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        return ScoreWindow(
            window_type="daily",
            window_start=window_end - timedelta(days=1),
            window_end=window_end,
        )

    async def generate_snapshots(
        self,
        *,
        window_type: str = "daily",
        now: datetime | None = None,
    ) -> list[AgentScoreSnapshot]:
        """生成一批 Agent 绩效快照。

        这个方法按时间窗口收集任务与审查结果，为每个 agent_tag 产出一条快照记录。
        """
        window = self.build_window(window_type=window_type, now=now)
        tasks = await self._load_tasks(window=window)
        if not tasks:
            return []

        reviews = await self._load_reviews(window=window)
        reviews_by_task_id = self._group_reviews_by_task(reviews=reviews)
        snapshots: list[AgentScoreSnapshot] = []

        for agent_tag, agent_tasks in self._group_tasks_by_agent(tasks=tasks).items():
            snapshot = AgentScoreSnapshot(
                id=str(uuid.uuid4()),
                agent_tag=agent_tag,
                window_type=window.window_type,
                window_start=window.window_start,
                window_end=window.window_end,
                pass_rate=self._calculate_pass_rate(agent_tasks=agent_tasks),
                handoff_rate=self._calculate_handoff_rate(agent_tasks=agent_tasks),
                avg_review_score=self._calculate_avg_review_score(
                    agent_tasks=agent_tasks,
                    reviews_by_task_id=reviews_by_task_id,
                ),
                avg_resolution_time_ms=self._calculate_avg_resolution_time_ms(agent_tasks=agent_tasks),
                rework_rate=self._calculate_rework_rate(agent_tasks=agent_tasks),
                violation_rate=self._calculate_violation_rate(
                    agent_tasks=agent_tasks,
                    reviews_by_task_id=reviews_by_task_id,
                ),
                payload=self._build_payload(
                    agent_tasks=agent_tasks,
                    reviews_by_task_id=reviews_by_task_id,
                ),
                created_at=now or datetime.now(),
            )
            snapshots.append(await self.snapshot_repo.create(snapshot))

        return snapshots

    async def _load_tasks(self, *, window: ScoreWindow) -> list[ComplaintTask]:
        """加载统计窗口内的任务。

        这个方法服务于绩效聚合，统一以任务完成时间为主，兼容尚未写 finished_at 的旧数据。
        """
        result = await self.session.execute(
            select(ComplaintTask).where(
                ComplaintTask.created_at >= window.window_start,
                ComplaintTask.created_at < window.window_end,
            )
        )
        return list(result.scalars().all())

    async def _load_reviews(self, *, window: ScoreWindow) -> list[ComplaintReview]:
        """加载统计窗口内的审查记录。

        这个方法服务于绩效聚合，提取 review 分数、驳回原因和转人工原因。
        """
        result = await self.session.execute(
            select(ComplaintReview).where(
                ComplaintReview.created_at >= window.window_start,
                ComplaintReview.created_at < window.window_end,
            )
        )
        return list(result.scalars().all())

    def _group_tasks_by_agent(self, *, tasks: list[ComplaintTask]) -> dict[str, list[ComplaintTask]]:
        """按 agent_tag 分组任务。

        这个方法服务于按岗位产出快照，避免不同执行岗位的数据混在一起。
        """
        grouped_tasks: dict[str, list[ComplaintTask]] = defaultdict(list)
        for task in tasks:
            grouped_tasks[task.agent_tag].append(task)
        return grouped_tasks

    def _group_reviews_by_task(
        self,
        *,
        reviews: list[ComplaintReview],
    ) -> dict[str, list[ComplaintReview]]:
        """按 task_id 分组审查记录。

        这个方法服务于把 review 得分和原因回挂到对应执行任务上。
        """
        grouped_reviews: dict[str, list[ComplaintReview]] = defaultdict(list)
        for review in reviews:
            grouped_reviews[review.task_id].append(review)
        return grouped_reviews

    def _calculate_pass_rate(self, *, agent_tasks: list[ComplaintTask]) -> float | None:
        """计算任务通过率。

        当前定义为：带 review_status 的任务里，review 通过占比多少。
        """
        reviewed_tasks = [task for task in agent_tasks if task.review_status]
        if not reviewed_tasks:
            return None
        passed_count = sum(
            1 for task in reviewed_tasks if task.review_status == ComplaintReviewStatus.PASSED.value
        )
        return passed_count / len(reviewed_tasks)

    def _calculate_handoff_rate(self, *, agent_tasks: list[ComplaintTask]) -> float | None:
        """计算转人工率。

        当前定义为：带 review_status 的任务里，被 escalated 的占比多少。
        """
        reviewed_tasks = [task for task in agent_tasks if task.review_status]
        if not reviewed_tasks:
            return None
        handoff_count = sum(
            1 for task in reviewed_tasks if task.review_status == ComplaintReviewStatus.ESCALATED.value
        )
        return handoff_count / len(reviewed_tasks)

    def _calculate_avg_review_score(
        self,
        *,
        agent_tasks: list[ComplaintTask],
        reviews_by_task_id: dict[str, list[ComplaintReview]],
    ) -> float | None:
        """计算平均审查分。

        这个方法服务于运营判断某岗位输出质量的总体水平。
        """
        scores: list[int] = []
        for task in agent_tasks:
            for review in reviews_by_task_id.get(task.id, []):
                if review.score is not None:
                    scores.append(review.score)
        if not scores:
            return None
        return sum(scores) / len(scores)

    def _calculate_avg_resolution_time_ms(self, *, agent_tasks: list[ComplaintTask]) -> int | None:
        """计算平均处理时长。

        这个方法服务于比较不同岗位的处理效率，避免只看通过率忽略耗时。
        """
        durations: list[int] = []
        for task in agent_tasks:
            if task.started_at is None or task.finished_at is None:
                continue
            durations.append(int((task.finished_at - task.started_at).total_seconds() * 1000))
        if not durations:
            return None
        return int(sum(durations) / len(durations))

    def _calculate_rework_rate(self, *, agent_tasks: list[ComplaintTask]) -> float | None:
        """计算返工率。

        当前定义为：带 review_status 的任务里，被 reviewer 驳回的占比多少。
        """
        reviewed_tasks = [task for task in agent_tasks if task.review_status]
        if not reviewed_tasks:
            return None
        rejected_count = sum(
            1 for task in reviewed_tasks if task.review_status == ComplaintReviewStatus.REJECTED.value
        )
        return rejected_count / len(reviewed_tasks)

    def _calculate_violation_rate(
        self,
        *,
        agent_tasks: list[ComplaintTask],
        reviews_by_task_id: dict[str, list[ComplaintReview]],
    ) -> float | None:
        """计算违规风险率。

        当前定义为：发生高风险 review 或低分 review 的任务占比多少。
        """
        reviewed_tasks = [task for task in agent_tasks if task.review_status]
        if not reviewed_tasks:
            return None

        violation_task_ids: set[str] = set()
        for task in reviewed_tasks:
            for review in reviews_by_task_id.get(task.id, []):
                if review.risk_level == "high" or (review.score is not None and review.score < 60):
                    violation_task_ids.add(task.id)
        return len(violation_task_ids) / len(reviewed_tasks)

    def _build_payload(
        self,
        *,
        agent_tasks: list[ComplaintTask],
        reviews_by_task_id: dict[str, list[ComplaintReview]],
    ) -> dict:
        """构建补充运营统计负载。

        这个方法服务于后续知识缺口分析和后台报表，先把高频驳回原因与转人工原因沉淀下来。
        """
        reject_reasons: Counter[str] = Counter()
        handoff_reasons: Counter[str] = Counter()
        reviewed_task_count = 0

        for task in agent_tasks:
            if task.review_status:
                reviewed_task_count += 1
            for review in reviews_by_task_id.get(task.id, []):
                reasons = list(review.reasons or [])
                if review.status == ComplaintReviewStatus.REJECTED.value:
                    reject_reasons.update(reasons)
                if review.status == ComplaintReviewStatus.ESCALATED.value:
                    handoff_reasons.update(reasons)

        return {
            "task_count": len(agent_tasks),
            "reviewed_task_count": reviewed_task_count,
            "reject_reasons_top": reject_reasons.most_common(5),
            "handoff_reasons_top": handoff_reasons.most_common(5),
        }
