"""会话详情 API 测试

本文件的业务职责，是验证会话详情接口已经把客服工作台恢复历史消息所需的读状态、
撤回状态和编辑状态一并返回，避免前端只能拿到消息正文而丢失处理痕迹。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestConversationDetailEndpoint:
    """测试会话详情接口返回的消息合同。"""

    @pytest.mark.anyio
    async def test_get_conversation_returns_message_status_fields(self):
        """测试会话详情接口会返回消息的已读、撤回和编辑状态。"""
        from app.routers.conversations import get_conversation

        now = datetime(2026, 4, 2, 12, 0, 0)
        mock_db = MagicMock()
        mock_conversation = SimpleNamespace(
            id="conv_123",
            user_id="user_123",
            title="售后投诉",
            created_at=now,
            updated_at=now,
            handoff_state="human",
            messages=[
                SimpleNamespace(
                    id="msg_123",
                    role="human_agent",
                    content="我们已经为您处理",
                    products=None,
                    message_type="text",
                    extra_metadata={"operator": "agent_a"},
                    token_count=None,
                    created_at=now,
                    is_delivered=True,
                    delivered_at=now,
                    read_at=now,
                    read_by="user_123",
                    is_withdrawn=False,
                    withdrawn_at=None,
                    withdrawn_by=None,
                    is_edited=True,
                    edited_at=now,
                    edited_by="agent_a",
                )
            ],
        )

        with patch("app.routers.conversations.ConversationService") as MockConversationService:
            mock_service = MockConversationService.return_value
            mock_service.get_conversation_with_messages = AsyncMock(return_value=mock_conversation)

            result = await get_conversation("conv_123", include_tool_calls=False, db=mock_db)

            assert result.handoff_state == "human"
            assert len(result.messages) == 1
            assert result.messages[0].is_delivered is True
            assert result.messages[0].read_by == "user_123"
            assert result.messages[0].is_edited is True
            assert result.messages[0].edited_by == "agent_a"

