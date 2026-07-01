"""客诉巡查调度任务测试

本文件的业务职责，是验证巡查服务已经被 scheduler 封装成可运行任务，
并且执行完成后会通知客服工作台刷新全局队列。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services.complaint.patrol_service import PatrolOutcome


class _FakeDbContext:
    """测试用数据库上下文。"""

    def __init__(self, session: SimpleNamespace):
        """持有当前调度任务测试需要的假数据库会话。"""
        self.session = session

    async def __aenter__(self) -> SimpleNamespace:
        """进入上下文时返回假数据库会话。"""
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        """退出上下文时不吞异常，确保任务执行失败会被测试捕获。"""
        return False


class TestComplaintPatrolTask:
    """测试客诉巡查调度任务。"""

    @pytest.mark.anyio
    async def test_run_executes_patrol_and_broadcasts_queue_refresh(self):
        """测试巡查任务跑完后会把变更广播给客服全局队列。"""
        from app.scheduler.tasks.complaint_patrol import ComplaintPatrolTask
        from app.schemas.websocket import WSAction, WSRole

        fake_session = SimpleNamespace()
        outcomes = [
            PatrolOutcome(
                ticket_id="ticket_123",
                conversation_id="conv_123",
                ticket_status="planned",
                patrol_status="auto_recovered",
                event_type="blocked_timeout",
                action_taken="已恢复",
                handoff_state="ai",
            ),
            PatrolOutcome(
                ticket_id="ticket_456",
                conversation_id="conv_456",
                ticket_status="handoff_pending",
                patrol_status="escalated",
                event_type="rework_loop",
                action_taken="已升级人工",
                handoff_state="pending",
            ),
        ]

        with patch(
            "app.scheduler.tasks.complaint_patrol.get_db_context",
            return_value=_FakeDbContext(fake_session),
        ):
            with patch(
                "app.scheduler.tasks.complaint_patrol.PatrolService"
            ) as MockPatrolService:
                with patch(
                    "app.scheduler.tasks.complaint_patrol.ws_manager.broadcast_to_role_global",
                    new=AsyncMock(return_value=2),
                ) as mock_broadcast_to_role_global:
                    mock_service = MockPatrolService.return_value
                    mock_service.run_patrol = AsyncMock(return_value=outcomes)

                    result = await ComplaintPatrolTask().run()

        mock_service.run_patrol.assert_awaited_once()
        assert mock_broadcast_to_role_global.await_count == 2
        first_call = mock_broadcast_to_role_global.await_args_list[0]
        second_call = mock_broadcast_to_role_global.await_args_list[1]
        assert first_call.args[0] == WSRole.AGENT
        assert first_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert first_call.args[1]["payload"]["source"] == "complaint_patrol_task"
        assert second_call.args[1]["payload"]["handoff_state"] == "pending"
        assert result.status.value == "success"
        assert result.data["outcome_count"] == 2
        assert result.data["recovered_count"] == 1
        assert result.data["escalated_count"] == 1
