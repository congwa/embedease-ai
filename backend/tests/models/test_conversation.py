"""Conversation 模型测试

测试会话模型在引入客诉主问题单快照后的字段、枚举和状态追踪能力。
"""


from app.models.conversation import Conversation, ConversationMode, HandoffState


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


class TestConversationModeEnum:
    """测试 ConversationMode 枚举"""

    def test_ai_mode_value(self):
        """测试 AI 模式值"""
        assert ConversationMode.AI.value == "ai"

    def test_pending_mode_value(self):
        """测试等待人工模式值"""
        assert ConversationMode.PENDING.value == "pending"

    def test_human_mode_value(self):
        """测试人工模式值"""
        assert ConversationMode.HUMAN.value == "human"

    def test_closed_mode_value(self):
        """测试关闭模式值"""
        assert ConversationMode.CLOSED.value == "closed"


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

    def test_has_conversation_mode_field(self):
        """测试有会话模式快照字段"""
        assert hasattr(Conversation, "conversation_mode")

    def test_has_current_ticket_id_field(self):
        """测试有当前主问题单字段"""
        assert hasattr(Conversation, "current_ticket_id")

    def test_has_complaint_status_field(self):
        """测试有客诉状态快照字段"""
        assert hasattr(Conversation, "complaint_status")

    def test_has_primary_issue_tag_field(self):
        """测试有主问题标签快照字段"""
        assert hasattr(Conversation, "primary_issue_tag")

    def test_has_current_agent_tag_field(self):
        """测试有当前责任岗位快照字段"""
        assert hasattr(Conversation, "current_agent_tag")

    def test_has_priority_level_field(self):
        """测试有优先级快照字段"""
        assert hasattr(Conversation, "priority_level")

    def test_has_risk_level_field(self):
        """测试有风险快照字段"""
        assert hasattr(Conversation, "risk_level")

    def test_has_unresolved_turns_field(self):
        """测试有未解决轮次字段"""
        assert hasattr(Conversation, "unresolved_turns")

    def test_has_review_status_field(self):
        """测试有审查状态快照字段"""
        assert hasattr(Conversation, "review_status")

    def test_has_review_score_field(self):
        """测试有审查分数字段"""
        assert hasattr(Conversation, "review_score")

    def test_has_block_reason_field(self):
        """测试有阻塞原因字段"""
        assert hasattr(Conversation, "block_reason")

    def test_has_secondary_issues_field(self):
        """测试有次级问题列表字段"""
        assert hasattr(Conversation, "secondary_issues")


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
