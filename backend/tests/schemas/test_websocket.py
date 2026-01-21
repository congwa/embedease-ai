"""WebSocket Schema 测试"""

import pytest
from pydantic import ValidationError

from app.schemas.websocket import (
    WSAction,
    WSErrorCode,
    WSRole,
    WSError,
    WSMessageBase,
    WS_PROTOCOL_VERSION,
    PingPayload,
    PongPayload,
    AckPayload,
    ConnectedPayload,
    ErrorPayload,
    UserSendMessagePayload,
    TypingPayload,
    ReadReceiptPayload,
    RequestHandoffPayload,
    AgentSendMessagePayload,
    StartHandoffPayload,
    EndHandoffPayload,
    TransferPayload,
    ServerMessagePayload,
    ServerTypingPayload,
    ServerReadReceiptPayload,
    HandoffStartedPayload,
    HandoffEndedPayload,
    UserPresencePayload,
    AgentPresencePayload,
    ConversationStatePayload,
    WithdrawMessagePayload,
    EditMessagePayload,
    MessageWithdrawnPayload,
    MessageEditedPayload,
    MessagesDeletedPayload,
    ACTION_PAYLOAD_MAP,
)


class TestWSErrorCode:
    """测试 WebSocket 错误码枚举"""

    def test_auth_error_codes(self):
        """测试认证相关错误码"""
        assert WSErrorCode.AUTH_REQUIRED == "AUTH_REQUIRED"
        assert WSErrorCode.AUTH_FAILED == "AUTH_FAILED"
        assert WSErrorCode.AUTH_EXPIRED == "AUTH_EXPIRED"

    def test_permission_error_codes(self):
        """测试权限相关错误码"""
        assert WSErrorCode.PERMISSION_DENIED == "PERMISSION_DENIED"
        assert WSErrorCode.NOT_IN_HUMAN_MODE == "NOT_IN_HUMAN_MODE"

    def test_request_error_codes(self):
        """测试请求相关错误码"""
        assert WSErrorCode.INVALID_ACTION == "INVALID_ACTION"
        assert WSErrorCode.INVALID_PAYLOAD == "INVALID_PAYLOAD"
        assert WSErrorCode.MISSING_FIELD == "MISSING_FIELD"

    def test_business_error_codes(self):
        """测试业务相关错误码"""
        assert WSErrorCode.CONVERSATION_NOT_FOUND == "CONVERSATION_NOT_FOUND"
        assert WSErrorCode.MESSAGE_SEND_FAILED == "MESSAGE_SEND_FAILED"


class TestWSRole:
    """测试 WebSocket 连接角色枚举"""

    def test_role_values(self):
        """测试角色值"""
        assert WSRole.USER == "user"
        assert WSRole.AGENT == "agent"


class TestWSAction:
    """测试 WebSocket Action 枚举"""

    def test_system_actions(self):
        """测试系统 Action"""
        assert WSAction.SYSTEM_PING == "system.ping"
        assert WSAction.SYSTEM_PONG == "system.pong"
        assert WSAction.SYSTEM_ACK == "system.ack"
        assert WSAction.SYSTEM_ERROR == "system.error"
        assert WSAction.SYSTEM_CONNECTED == "system.connected"

    def test_client_user_actions(self):
        """测试客户端用户 Action"""
        assert WSAction.CLIENT_USER_SEND_MESSAGE == "client.user.send_message"
        assert WSAction.CLIENT_USER_TYPING == "client.user.typing"
        assert WSAction.CLIENT_USER_READ == "client.user.read"
        assert WSAction.CLIENT_USER_REQUEST_HANDOFF == "client.user.request_handoff"

    def test_client_agent_actions(self):
        """测试客户端客服 Action"""
        assert WSAction.CLIENT_AGENT_SEND_MESSAGE == "client.agent.send_message"
        assert WSAction.CLIENT_AGENT_START_HANDOFF == "client.agent.start_handoff"
        assert WSAction.CLIENT_AGENT_END_HANDOFF == "client.agent.end_handoff"

    def test_server_push_actions(self):
        """测试服务器推送 Action"""
        assert WSAction.SERVER_MESSAGE == "server.message"
        assert WSAction.SERVER_TYPING == "server.typing"
        assert WSAction.SERVER_HANDOFF_STARTED == "server.handoff_started"


class TestWSError:
    """测试错误信息结构"""

    def test_basic_error(self):
        """测试基本错误"""
        error = WSError(code="TEST_ERROR", message="测试错误")
        assert error.code == "TEST_ERROR"
        assert error.message == "测试错误"
        assert error.detail is None

    def test_error_with_detail(self):
        """测试带详情的错误"""
        error = WSError(
            code="VALIDATION_ERROR",
            message="验证失败",
            detail={"field": "content", "reason": "too_long"},
        )
        assert error.detail["field"] == "content"


class TestWSMessageBase:
    """测试 WebSocket 消息基础结构"""

    def test_required_fields(self):
        """测试必填字段"""
        msg = WSMessageBase(
            id="msg_123",
            ts=1704067200000,
            action="system.ping",
        )
        assert msg.id == "msg_123"
        assert msg.ts == 1704067200000
        assert msg.action == "system.ping"
        assert msg.v == WS_PROTOCOL_VERSION

    def test_optional_fields(self):
        """测试可选字段"""
        msg = WSMessageBase(
            id="msg_456",
            ts=1704067200000,
            action="server.message",
            conversation_id="conv_789",
            reply_to="msg_123",
        )
        assert msg.conversation_id == "conv_789"
        assert msg.reply_to == "msg_123"

    def test_with_error(self):
        """测试带错误的消息"""
        msg = WSMessageBase(
            id="msg_err",
            ts=1704067200000,
            action="system.error",
            error=WSError(code="TEST", message="测试"),
        )
        assert msg.error is not None
        assert msg.error.code == "TEST"


class TestSystemPayloads:
    """测试系统 Payload"""

    def test_ping_payload(self):
        """测试心跳请求"""
        payload = PingPayload()
        assert payload is not None

    def test_pong_payload(self):
        """测试心跳响应"""
        payload = PongPayload(server_ts=1704067200000)
        assert payload.server_ts == 1704067200000

    def test_ack_payload(self):
        """测试消息确认"""
        payload = AckPayload(received_id="msg_123", status="ok")
        assert payload.received_id == "msg_123"
        assert payload.status == "ok"

    def test_connected_payload(self):
        """测试连接成功"""
        payload = ConnectedPayload(
            connection_id="conn_123",
            role="user",
            conversation_id="conv_456",
            handoff_state="none",
            peer_online=True,
            unread_count=5,
        )
        assert payload.connection_id == "conn_123"
        assert payload.peer_online is True
        assert payload.unread_count == 5

    def test_error_payload(self):
        """测试错误通知"""
        payload = ErrorPayload(
            code="INVALID_ACTION",
            message="无效的操作",
        )
        assert payload.code == "INVALID_ACTION"


class TestClientUserPayloads:
    """测试客户端用户 Payload"""

    def test_user_send_message(self):
        """测试用户发送消息"""
        payload = UserSendMessagePayload(content="你好")
        assert payload.content == "你好"

    def test_user_send_message_with_id(self):
        """测试带 ID 的消息"""
        payload = UserSendMessagePayload(
            content="测试消息",
            message_id="client_msg_123",
        )
        assert payload.message_id == "client_msg_123"

    def test_typing_payload(self):
        """测试输入状态"""
        payload = TypingPayload(is_typing=True)
        assert payload.is_typing is True

    def test_read_receipt_payload(self):
        """测试已读回执"""
        payload = ReadReceiptPayload(message_ids=["msg_1", "msg_2", "msg_3"])
        assert len(payload.message_ids) == 3

    def test_request_handoff_payload(self):
        """测试请求人工客服"""
        payload = RequestHandoffPayload(reason="问题太复杂")
        assert payload.reason == "问题太复杂"


class TestClientAgentPayloads:
    """测试客户端客服 Payload"""

    def test_agent_send_message(self):
        """测试客服发送消息"""
        payload = AgentSendMessagePayload(content="您好，有什么可以帮您？")
        assert payload.content == "您好，有什么可以帮您？"

    def test_start_handoff_payload(self):
        """测试客服主动介入"""
        payload = StartHandoffPayload(reason="用户需要帮助")
        assert payload.reason == "用户需要帮助"

    def test_end_handoff_payload(self):
        """测试结束客服介入"""
        payload = EndHandoffPayload(summary="问题已解决")
        assert payload.summary == "问题已解决"

    def test_transfer_payload(self):
        """测试转接客服"""
        payload = TransferPayload(
            target_agent_id="agent_456",
            reason="专业问题",
        )
        assert payload.target_agent_id == "agent_456"


class TestServerPushPayloads:
    """测试服务器推送 Payload"""

    def test_server_message_payload(self):
        """测试服务器推送新消息"""
        payload = ServerMessagePayload(
            message_id="msg_123",
            role="assistant",
            content="这是 AI 的回复",
            created_at="2024-01-01T12:00:00Z",
        )
        assert payload.message_id == "msg_123"
        assert payload.role == "assistant"

    def test_server_typing_payload(self):
        """测试对方输入状态"""
        payload = ServerTypingPayload(role="user", is_typing=True)
        assert payload.role == "user"
        assert payload.is_typing is True

    def test_server_read_receipt_payload(self):
        """测试已读回执推送"""
        payload = ServerReadReceiptPayload(
            role="user",
            message_ids=["msg_1", "msg_2"],
            read_at="2024-01-01T12:00:00Z",
            read_by="user_123",
        )
        assert len(payload.message_ids) == 2

    def test_handoff_started_payload(self):
        """测试客服介入开始"""
        payload = HandoffStartedPayload(operator="agent_123", reason="用户请求")
        assert payload.operator == "agent_123"

    def test_handoff_ended_payload(self):
        """测试客服介入结束"""
        payload = HandoffEndedPayload(operator="agent_123", summary="问题解决")
        assert payload.summary == "问题解决"

    def test_user_presence_payload(self):
        """测试用户在线状态"""
        payload = UserPresencePayload(
            user_id="user_123",
            conversation_id="conv_456",
            online=True,
        )
        assert payload.online is True

    def test_agent_presence_payload(self):
        """测试客服在线状态"""
        payload = AgentPresencePayload(operator="agent_123", online=False)
        assert payload.online is False

    def test_conversation_state_payload(self):
        """测试会话状态"""
        payload = ConversationStatePayload(
            handoff_state="active",
            operator="agent_123",
        )
        assert payload.handoff_state == "active"


class TestMessageEditPayloads:
    """测试消息撤回/编辑 Payload"""

    def test_withdraw_message_payload(self):
        """测试撤回消息请求"""
        payload = WithdrawMessagePayload(
            message_id="msg_123",
            reason="发错了",
        )
        assert payload.message_id == "msg_123"
        assert payload.reason == "发错了"

    def test_edit_message_payload(self):
        """测试编辑消息请求"""
        payload = EditMessagePayload(
            message_id="msg_123",
            new_content="修改后的内容",
            regenerate=True,
        )
        assert payload.new_content == "修改后的内容"
        assert payload.regenerate is True

    def test_message_withdrawn_payload(self):
        """测试消息已撤回通知"""
        payload = MessageWithdrawnPayload(
            message_id="msg_123",
            withdrawn_by="agent_456",
            withdrawn_at="2024-01-01T12:00:00Z",
        )
        assert payload.withdrawn_by == "agent_456"

    def test_message_edited_payload(self):
        """测试消息已编辑通知"""
        payload = MessageEditedPayload(
            message_id="msg_123",
            old_content="旧内容",
            new_content="新内容",
            edited_by="agent_456",
            edited_at="2024-01-01T12:00:00Z",
            deleted_message_ids=["msg_124", "msg_125"],
            regenerate_triggered=True,
        )
        assert len(payload.deleted_message_ids) == 2
        assert payload.regenerate_triggered is True

    def test_messages_deleted_payload(self):
        """测试消息已删除通知"""
        payload = MessagesDeletedPayload(
            message_ids=["msg_1", "msg_2", "msg_3"],
            reason="edit_regenerate",
        )
        assert len(payload.message_ids) == 3


class TestActionPayloadMap:
    """测试 Action-Payload 映射"""

    def test_system_actions_mapped(self):
        """测试系统 Action 映射"""
        assert ACTION_PAYLOAD_MAP[WSAction.SYSTEM_PING] == PingPayload
        assert ACTION_PAYLOAD_MAP[WSAction.SYSTEM_PONG] == PongPayload
        assert ACTION_PAYLOAD_MAP[WSAction.SYSTEM_ACK] == AckPayload

    def test_client_user_actions_mapped(self):
        """测试客户端用户 Action 映射"""
        assert ACTION_PAYLOAD_MAP[WSAction.CLIENT_USER_SEND_MESSAGE] == UserSendMessagePayload
        assert ACTION_PAYLOAD_MAP[WSAction.CLIENT_USER_TYPING] == TypingPayload

    def test_server_actions_mapped(self):
        """测试服务器 Action 映射"""
        assert ACTION_PAYLOAD_MAP[WSAction.SERVER_MESSAGE] == ServerMessagePayload
        assert ACTION_PAYLOAD_MAP[WSAction.SERVER_TYPING] == ServerTypingPayload
