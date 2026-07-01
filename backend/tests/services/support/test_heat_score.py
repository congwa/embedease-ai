"""客服热度与统计服务测试

本文件的业务职责，是验证客服统计接口在计算高热会话时不会额外查询列表消息预览，
避免顶部红点接口承担不必要的 N+1 风险。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.conversation import HandoffState


class TestSupportStats:
    """测试客服统计服务。"""

    @pytest.mark.anyio
    async def test_get_support_stats_skips_message_preview_when_counting_hot_conversations(self):
        """测试统计接口复用热度计算时会关闭消息预览查询。"""
        from app.services.support.heat_score import get_support_stats

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(
                    all=MagicMock(
                        return_value=[
                            MagicMock(handoff_state=HandoffState.PENDING.value, count=2),
                            MagicMock(handoff_state=HandoffState.HUMAN.value, count=1),
                        ]
                    )
                ),
                MagicMock(scalar=MagicMock(return_value=5)),
            ]
        )

        with patch(
            "app.services.support.heat_score.get_conversations_with_heat",
            new=AsyncMock(return_value=([{"heat_score": 88}, {"heat_score": 40}], 2)),
        ) as mock_get_conversations:
            result = await get_support_stats(mock_session)

            assert result["pending_count"] == 2
            assert result["human_count"] == 1
            assert result["total_unread"] == 5
            assert result["high_heat_count"] == 1
            mock_get_conversations.assert_awaited_once_with(
                mock_session,
                sort_by="heat",
                limit=100,
                include_message_preview=False,
            )

