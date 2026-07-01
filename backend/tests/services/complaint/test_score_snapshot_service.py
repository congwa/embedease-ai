"""ScoreSnapshotService 测试

本文件的业务职责，是验证客诉绩效快照能把 task/review 聚合成可运营的指标结果，
避免 agent_score_snapshot 只停留在表结构层面。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.schemas.complaint import ComplaintReviewStatus, ComplaintTaskStatus
from app.services.complaint.score_snapshot_service import ScoreSnapshotService


def build_task(
    *,
    task_id: str,
    agent_tag: str,
    review_status: str,
    started_at: datetime,
    finished_at: datetime,
) -> ComplaintTask:
    """构造一条基础绩效统计任务。

    这个方法服务于绩效聚合测试，表达某个岗位在统计窗口中的一次执行结果。
    """
    return ComplaintTask(
        id=task_id,
        ticket_id=f"ticket_{task_id}",
        task_type="resolution",
        agent_tag=agent_tag,
        status=ComplaintTaskStatus.DONE.value,
        review_required=True,
        review_status=review_status,
        started_at=started_at,
        finished_at=finished_at,
        created_at=started_at,
        updated_at=finished_at,
    )


def build_review(
    *,
    review_id: str,
    task_id: str,
    status: str,
    score: int,
    reasons: list[str],
    created_at: datetime,
    risk_level: str = "medium",
) -> ComplaintReview:
    """构造一条基础绩效统计 review。

    这个方法服务于平均分、违规率和高频原因聚合测试。
    """
    return ComplaintReview(
        id=review_id,
        ticket_id=f"ticket_{task_id}",
        task_id=task_id,
        reviewer_agent_tag="quality_reviewer_agent",
        status=status,
        score=score,
        risk_level=risk_level,
        reasons=reasons,
        created_at=created_at,
        updated_at=created_at,
    )


class _FakeResult:
    """测试用查询结果容器。"""

    def __init__(self, items: list):
        """持有当前查询应该返回的数据集合。"""
        self.items = items

    def scalars(self) -> "_FakeResult":
        """模拟 SQLAlchemy scalars() 链式调用。"""
        return self

    def all(self) -> list:
        """返回当前查询数据集合。"""
        return self.items


class TestScoreSnapshotService:
    """测试绩效快照服务。"""

    @pytest.mark.anyio
    async def test_generate_snapshots_aggregates_task_and_review_metrics(self):
        """测试绩效快照会按 agent_tag 聚合通过率、返工率和平均分。"""
        mock_session = MagicMock()
        service = ScoreSnapshotService(mock_session)
        now = datetime(2026, 4, 3, 2, 30, 0)
        task_started_at = now - timedelta(hours=5)
        task_finished_at = task_started_at + timedelta(minutes=10)

        tasks = [
            build_task(
                task_id="task_pass",
                agent_tag="resolution_execution_agent",
                review_status=ComplaintReviewStatus.PASSED.value,
                started_at=task_started_at,
                finished_at=task_finished_at,
            ),
            build_task(
                task_id="task_reject",
                agent_tag="resolution_execution_agent",
                review_status=ComplaintReviewStatus.REJECTED.value,
                started_at=task_started_at + timedelta(minutes=15),
                finished_at=task_finished_at + timedelta(minutes=15),
            ),
            build_task(
                task_id="task_escalated",
                agent_tag="handoff_orchestrator_agent",
                review_status=ComplaintReviewStatus.ESCALATED.value,
                started_at=task_started_at + timedelta(minutes=30),
                finished_at=task_finished_at + timedelta(minutes=30),
            ),
        ]
        reviews = [
            build_review(
                review_id="review_pass",
                task_id="task_pass",
                status=ComplaintReviewStatus.PASSED.value,
                score=95,
                reasons=[],
                created_at=task_finished_at,
            ),
            build_review(
                review_id="review_reject",
                task_id="task_reject",
                status=ComplaintReviewStatus.REJECTED.value,
                score=58,
                reasons=["缺少订单号"],
                created_at=task_finished_at + timedelta(minutes=15),
                risk_level="high",
            ),
            build_review(
                review_id="review_escalated",
                task_id="task_escalated",
                status=ComplaintReviewStatus.ESCALATED.value,
                score=40,
                reasons=["高风险赔付"],
                created_at=task_finished_at + timedelta(minutes=30),
                risk_level="high",
            ),
        ]

        mock_session.execute = AsyncMock(
            side_effect=[
                _FakeResult(tasks),
                _FakeResult(reviews),
            ]
        )
        service.snapshot_repo.create = AsyncMock(side_effect=lambda snapshot: snapshot)

        snapshots = await service.generate_snapshots(window_type="daily", now=now)

        assert len(snapshots) == 2
        snapshots_by_agent = {snapshot.agent_tag: snapshot for snapshot in snapshots}

        resolution_snapshot = snapshots_by_agent["resolution_execution_agent"]
        assert resolution_snapshot.pass_rate == 0.5
        assert resolution_snapshot.rework_rate == 0.5
        assert resolution_snapshot.avg_review_score == 76.5
        assert resolution_snapshot.avg_resolution_time_ms == 600000
        assert resolution_snapshot.violation_rate == 0.5
        assert resolution_snapshot.payload == {
            "task_count": 2,
            "reviewed_task_count": 2,
            "reject_reasons_top": [("缺少订单号", 1)],
            "handoff_reasons_top": [],
        }

        handoff_snapshot = snapshots_by_agent["handoff_orchestrator_agent"]
        assert handoff_snapshot.handoff_rate == 1.0
        assert handoff_snapshot.pass_rate == 0.0
        assert handoff_snapshot.payload["handoff_reasons_top"] == [("高风险赔付", 1)]

    def test_build_window_supports_hourly_and_daily(self):
        """测试绩效统计窗口支持日窗和小时窗。"""
        mock_session = MagicMock()
        service = ScoreSnapshotService(mock_session)
        now = datetime(2026, 4, 3, 10, 45, 0)

        hourly_window = service.build_window(window_type="hourly", now=now)
        daily_window = service.build_window(window_type="daily", now=now)

        assert hourly_window.window_start == datetime(2026, 4, 3, 9, 0, 0)
        assert hourly_window.window_end == datetime(2026, 4, 3, 10, 0, 0)
        assert daily_window.window_start == datetime(2026, 4, 2, 0, 0, 0)
        assert daily_window.window_end == datetime(2026, 4, 3, 0, 0, 0)
