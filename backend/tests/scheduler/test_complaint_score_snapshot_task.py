"""客诉绩效快照调度任务测试

本文件的业务职责，是验证绩效快照统计已经接入 scheduler，
可以被后台任务稳定触发并返回基础统计结果。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


class _FakeDbContext:
    """测试用数据库上下文。"""

    def __init__(self, session: SimpleNamespace):
        """持有当前调度任务测试需要的假数据库会话。"""
        self.session = session

    async def __aenter__(self) -> SimpleNamespace:
        """进入上下文时返回假数据库会话。"""
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        """退出上下文时不吞异常，确保统计任务异常能被测试捕获。"""
        return False


class TestComplaintScoreSnapshotTask:
    """测试客诉绩效快照任务。"""

    @pytest.mark.anyio
    async def test_run_generates_snapshots(self):
        """测试绩效快照任务会调用聚合服务并返回统计结果。"""
        from app.scheduler.tasks.complaint_score_snapshot import ComplaintScoreSnapshotTask

        fake_session = SimpleNamespace()
        fake_snapshots = [
            SimpleNamespace(agent_tag="resolution_execution_agent", created_at=datetime(2026, 4, 3, 2, 30, 0)),
            SimpleNamespace(agent_tag="handoff_orchestrator_agent", created_at=datetime(2026, 4, 3, 2, 30, 0)),
        ]

        with patch(
            "app.scheduler.tasks.complaint_score_snapshot.get_db_context",
            return_value=_FakeDbContext(fake_session),
        ):
            with patch(
                "app.scheduler.tasks.complaint_score_snapshot.ScoreSnapshotService"
            ) as MockScoreSnapshotService:
                mock_service = MockScoreSnapshotService.return_value
                mock_service.generate_snapshots = AsyncMock(return_value=fake_snapshots)

                result = await ComplaintScoreSnapshotTask().run()

        mock_service.generate_snapshots.assert_awaited_once_with(window_type="daily")
        assert result.status.value == "success"
        assert result.data["snapshot_count"] == 2
        assert result.data["agent_tags"] == [
            "resolution_execution_agent",
            "handoff_orchestrator_agent",
        ]
