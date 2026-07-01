"""客服绩效快照 API 测试

本文件的业务职责，是验证 support 路由已经暴露 Agent 绩效快照读取接口，
后续运营后台可以直接消费后台统计结果，而不必临时扫全量 task/review。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSupportScoreSnapshotEndpoint:
    """测试绩效快照读取接口。"""

    @pytest.mark.anyio
    async def test_list_agent_score_snapshots_returns_recent_items(self):
        """测试接口会返回最近一批指定窗口类型的绩效快照。"""
        from app.routers.support import list_agent_score_snapshots

        mock_db = MagicMock()
        snapshots = [
            MagicMock(
                id="snapshot_123",
                agent_tag="resolution_execution_agent",
                window_type="daily",
                window_start=datetime(2026, 4, 2, 0, 0, 0),
                window_end=datetime(2026, 4, 3, 0, 0, 0),
                pass_rate=0.9,
                handoff_rate=0.1,
                avg_review_score=92.5,
                avg_resolution_time_ms=180000,
                rework_rate=0.05,
                violation_rate=0.0,
                payload={"task_count": 20},
                created_at=datetime(2026, 4, 3, 2, 30, 0),
            )
        ]

        with patch("app.routers.support.AgentScoreSnapshotRepository") as MockSnapshotRepo:
            mock_repo = MockSnapshotRepo.return_value
            mock_repo.list_by_window_type = AsyncMock(return_value=snapshots)

            result = await list_agent_score_snapshots(
                window_type="daily",
                limit=10,
                db=mock_db,
            )

        mock_repo.list_by_window_type.assert_awaited_once_with("daily", limit=10)
        assert result.total == 1
        assert result.window_type == "daily"
        assert result.items[0].agent_tag == "resolution_execution_agent"
        assert result.items[0].payload == {"task_count": 20}
