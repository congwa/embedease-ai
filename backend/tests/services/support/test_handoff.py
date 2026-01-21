"""HandoffService 测试

测试客服介入状态管理服务的状态机、方法和边界条件。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.models.conversation import HandoffState
from app.services.support.handoff import HandoffService


class TestHandoffStateEnum:
    """测试 HandoffState 枚举"""

    def test_ai_state(self):
        """测试 AI 状态"""
        assert HandoffState.AI.value == "ai"

    def test_human_state(self):
        """测试 HUMAN 状态"""
        assert HandoffState.HUMAN.value == "human"

    def test_pending_state(self):
        """测试 PENDING 状态"""
        assert HandoffState.PENDING.value == "pending"

    def test_all_states_defined(self):
        """测试所有状态都已定义"""
        states = [s.value for s in HandoffState]
        assert "ai" in states
        assert "human" in states
        assert "pending" in states


class TestHandoffServiceInit:
    """测试 HandoffService 初始化"""

    def test_init_with_session(self):
        """测试使用 session 初始化"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)
        assert service.session is mock_session


class TestHandoffStateMachine:
    """测试 Handoff 状态机转换"""

    @pytest.mark.anyio
    async def test_get_handoff_state(self):
        """测试获取 handoff 状态"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        state = await service.get_handoff_state("conv_123")
        assert state == "ai"

    @pytest.mark.anyio
    async def test_get_handoff_state_not_found(self):
        """测试获取不存在会话的状态"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)
        service.get_conversation = AsyncMock(return_value=None)

        state = await service.get_handoff_state("invalid_id")
        assert state is None

    @pytest.mark.anyio
    async def test_is_human_mode_true(self):
        """测试 is_human_mode 为 True"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.HUMAN.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.is_human_mode("conv_123")
        assert result is True

    @pytest.mark.anyio
    async def test_is_human_mode_false(self):
        """测试 is_human_mode 为 False"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.is_human_mode("conv_123")
        assert result is False


class TestStartHandoff:
    """测试开始人工介入"""

    @pytest.mark.anyio
    async def test_start_handoff_success(self):
        """测试成功开始介入"""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.start_handoff(
            "conv_123",
            operator="admin",
            reason="用户请求人工服务",
        )

        assert result["success"] is True
        assert result["conversation_id"] == "conv_123"
        assert result["operator"] == "admin"
        assert result["handoff_state"] == HandoffState.HUMAN.value

    @pytest.mark.anyio
    async def test_start_handoff_not_found(self):
        """测试会话不存在时开始介入"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)
        service.get_conversation = AsyncMock(return_value=None)

        result = await service.start_handoff(
            "invalid_id",
            operator="admin",
        )

        assert result["success"] is False
        assert "会话不存在" in result["error"]

    @pytest.mark.anyio
    async def test_start_handoff_already_human(self):
        """测试已在人工模式时开始介入"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.HUMAN.value
        mock_conversation.handoff_operator = "existing_admin"
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.start_handoff(
            "conv_123",
            operator="new_admin",
        )

        assert result["success"] is False
        assert "已在人工模式" in result["error"]
        assert result["current_operator"] == "existing_admin"


class TestEndHandoff:
    """测试结束人工介入"""

    @pytest.mark.anyio
    async def test_end_handoff_success(self):
        """测试成功结束介入"""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.HUMAN.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.end_handoff(
            "conv_123",
            operator="admin",
            summary="问题已解决",
        )

        assert result["success"] is True
        assert result["conversation_id"] == "conv_123"
        assert result["ended_by"] == "admin"
        assert result["handoff_state"] == HandoffState.AI.value

    @pytest.mark.anyio
    async def test_end_handoff_not_found(self):
        """测试会话不存在时结束介入"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)
        service.get_conversation = AsyncMock(return_value=None)

        result = await service.end_handoff(
            "invalid_id",
            operator="admin",
        )

        assert result["success"] is False
        assert "会话不存在" in result["error"]

    @pytest.mark.anyio
    async def test_end_handoff_not_human_mode(self):
        """测试未在人工模式时结束介入"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.end_handoff(
            "conv_123",
            operator="admin",
        )

        assert result["success"] is False
        assert "未在人工模式" in result["error"]


class TestAddHumanMessage:
    """测试添加人工客服消息"""

    @pytest.mark.anyio
    async def test_add_human_message_success(self):
        """测试成功添加人工消息"""
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.HUMAN.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        message = await service.add_human_message(
            "conv_123",
            content="您好，有什么可以帮您？",
            operator="admin",
        )

        assert message is not None
        mock_session.add.assert_called_once()

    @pytest.mark.anyio
    async def test_add_human_message_not_human_mode(self):
        """测试非人工模式下添加消息"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        message = await service.add_human_message(
            "conv_123",
            content="消息",
            operator="admin",
        )

        assert message is None

    @pytest.mark.anyio
    async def test_add_human_message_not_found(self):
        """测试会话不存在时添加消息"""
        mock_session = MagicMock()
        service = HandoffService(mock_session)
        service.get_conversation = AsyncMock(return_value=None)

        message = await service.add_human_message(
            "invalid_id",
            content="消息",
            operator="admin",
        )

        assert message is None


class TestHandoffEdgeCases:
    """测试 Handoff 边界条件"""

    @pytest.mark.anyio
    async def test_empty_operator(self):
        """测试空客服标识"""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.start_handoff(
            "conv_123",
            operator="",  # 空标识
        )

        # 业务逻辑应该处理这种情况
        assert result is not None

    @pytest.mark.anyio
    async def test_empty_reason(self):
        """测试空介入原因"""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        service = HandoffService(mock_session)

        mock_conversation = MagicMock()
        mock_conversation.handoff_state = HandoffState.AI.value
        service.get_conversation = AsyncMock(return_value=mock_conversation)

        result = await service.start_handoff(
            "conv_123",
            operator="admin",
            reason="",  # 空原因
        )

        assert result["success"] is True

    @pytest.mark.anyio
    async def test_update_notification_time(self):
        """测试更新通知时间"""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        service = HandoffService(mock_session)

        # 不应该抛出异常
        await service.update_notification_time("conv_123")
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
