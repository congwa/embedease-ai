"""Conversation 模型测试

测试会话模型的字段、枚举和状态追踪。
"""

import pytest
from datetime import datetime

from app.models.conversation import Conversation, HandoffState


class TestHandoffStateEnum:
    """测试 HandoffState 枚举"""

    def test_ai_state_value(self):
        """测试 AI 状态值"""
        assert HandoffState.AI.value == "ai"

    def test_human_state_value(self):
        """测试 HUMAN 状态值"""
        assert HandoffState.HUMAN.value == "human"

    def test_pending_state_value(self):
        """测试 PENDING 状态值"""
        assert HandoffState.PENDING.value == "pending"

    def test_enum_members(self):
        """测试枚举成员"""
        members = list(HandoffState)
        assert len(members) >= 3
        assert HandoffState.AI in members
        assert HandoffState.HUMAN in members
        assert HandoffState.PENDING in members

    def test_state_comparison(self):
        """测试状态比较"""
        assert HandoffState.AI != HandoffState.HUMAN
        assert HandoffState.AI == HandoffState.AI

    def test_state_from_value(self):
        """测试从值获取状态"""
        assert HandoffState("ai") == HandoffState.AI
        assert HandoffState("human") == HandoffState.HUMAN
        assert HandoffState("pending") == HandoffState.PENDING


class TestConversationModelStructure:
    """测试 Conversation 模型结构"""

    def test_has_id_field(self):
        """测试有 id 字段"""
        assert hasattr(Conversation, 'id')

    def test_has_user_id_field(self):
        """测试有 user_id 字段"""
        assert hasattr(Conversation, 'user_id')

    def test_has_title_field(self):
        """测试有 title 字段"""
        assert hasattr(Conversation, 'title')

    def test_has_handoff_state_field(self):
        """测试有 handoff_state 字段"""
        assert hasattr(Conversation, 'handoff_state')

    def test_has_handoff_operator_field(self):
        """测试有 handoff_operator 字段"""
        assert hasattr(Conversation, 'handoff_operator')

    def test_has_handoff_reason_field(self):
        """测试有 handoff_reason 字段"""
        assert hasattr(Conversation, 'handoff_reason')

    def test_has_handoff_at_field(self):
        """测试有 handoff_at 字段"""
        assert hasattr(Conversation, 'handoff_at')


class TestConversationOnlineTracking:
    """测试会话在线状态追踪"""

    def test_has_user_online_field(self):
        """测试有 user_online 字段"""
        assert hasattr(Conversation, 'user_online')

    def test_has_user_last_online_at_field(self):
        """测试有 user_last_online_at 字段"""
        assert hasattr(Conversation, 'user_last_online_at')

    def test_has_agent_online_field(self):
        """测试有 agent_online 字段"""
        assert hasattr(Conversation, 'agent_online')

    def test_has_agent_last_online_at_field(self):
        """测试有 agent_last_online_at 字段"""
        assert hasattr(Conversation, 'agent_last_online_at')

    def test_has_current_agent_id_field(self):
        """测试有 current_agent_id 字段"""
        assert hasattr(Conversation, 'current_agent_id')


class TestConversationGreeting:
    """测试会话开场白相关"""

    def test_has_greeting_sent_field(self):
        """测试有 greeting_sent 字段"""
        assert hasattr(Conversation, 'greeting_sent')

    def test_has_agent_id_field(self):
        """测试有 agent_id 字段"""
        assert hasattr(Conversation, 'agent_id')


class TestConversationTimestamps:
    """测试会话时间戳"""

    def test_has_created_at_field(self):
        """测试有 created_at 字段"""
        assert hasattr(Conversation, 'created_at')

    def test_has_updated_at_field(self):
        """测试有 updated_at 字段"""
        assert hasattr(Conversation, 'updated_at')

    def test_has_last_notification_at_field(self):
        """测试有 last_notification_at 字段"""
        assert hasattr(Conversation, 'last_notification_at')


class TestConversationTableName:
    """测试表名"""

    def test_table_name(self):
        """测试表名正确"""
        assert Conversation.__tablename__ == "conversations"
