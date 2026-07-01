"""客服 WebSocket Handler 测试

本文件的业务职责，是验证客服在详情页执行已读、发消息、编辑和撤回后，
用户端与客服工作台都会收到正确的实时事件，确保队列优先级和最新动态不失真。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.websocket import WSAction, WSRole


class _FakeServicesContext:
    """测试用服务容器上下文。"""

    def __init__(self, services: SimpleNamespace):
        """持有当前用例需要的假服务集合。"""
        self.services = services

    async def __aenter__(self) -> SimpleNamespace:
        """进入上下文时返回假服务容器，模拟真实依赖注入。"""
        return self.services

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        """退出上下文时不吞掉异常，保持测试对失败敏感。"""
        return False


class TestAgentReadHandler:
    """测试客服已读处理器。"""

    @pytest.mark.anyio
    async def test_handle_agent_read_broadcasts_user_receipt_and_agent_state(self):
        """测试客服已读后会同时通知用户端和客服端状态。"""
        from app.services.websocket.handlers.agent import handle_agent_read

        read_at = datetime(2026, 4, 2, 17, 20, 0)
        conn = SimpleNamespace(
            id="conn_123",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            message_repo=SimpleNamespace(
                mark_as_read=AsyncMock(return_value=(2, read_at)),
                get_unread_count=AsyncMock(return_value=0),
            ),
            support_state=SimpleNamespace(
                build_websocket_state_payload=AsyncMock(
                    return_value={
                        "handoff_state": "human",
                        "unread_count": 0,
                        "user_online": True,
                    }
                )
            ),
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_role_global",
                    new=AsyncMock(return_value=1),
                ) as mock_broadcast_to_role_global:
                    await handle_agent_read(
                        conn,
                        WSAction.CLIENT_AGENT_READ,
                        {"message_ids": ["msg_1", "msg_2"]},
                    )

                    assert mock_send_to_role.await_count == 2
                    first_call = mock_send_to_role.await_args_list[0]
                    second_call = mock_send_to_role.await_args_list[1]

                    assert first_call.args[0] == "conv_123"
                    assert first_call.args[1] == WSRole.USER
                    assert first_call.args[2]["action"] == WSAction.SERVER_READ_RECEIPT

                    assert second_call.args[0] == "conv_123"
                    assert second_call.args[1] == WSRole.AGENT
                    assert second_call.args[2]["action"] == WSAction.SERVER_CONVERSATION_STATE
                    mock_broadcast_to_role_global.assert_awaited_once()
                    global_call = mock_broadcast_to_role_global.await_args
                    assert global_call.args[0] == WSRole.AGENT
                    assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
                    assert global_call.args[1]["payload"]["source"] == "agent_read"


class TestAgentSendMessageHandler:
    """测试客服发消息处理器。"""

    @pytest.mark.anyio
    async def test_handle_agent_send_message_broadcasts_to_user_and_agents(self):
        """测试人工消息会同时广播到用户端和客服端，并携带送达状态。"""
        from app.services.websocket.handlers.agent import handle_agent_send_message

        created_at = datetime(2026, 4, 2, 17, 30, 0)
        conn = SimpleNamespace(
            id="conn_456",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            handoff=SimpleNamespace(
                add_human_message=AsyncMock(
                    return_value=SimpleNamespace(id="client_msg_123", created_at=created_at)
                )
            ),
            message_repo=SimpleNamespace(
                mark_as_delivered=AsyncMock(return_value=1),
            ),
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(side_effect=[1, 2]),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_role_global",
                    new=AsyncMock(return_value=1),
                ) as mock_broadcast_to_role_global:
                    await handle_agent_send_message(
                        conn,
                        WSAction.CLIENT_AGENT_SEND_MESSAGE,
                        {
                            "content": "请您稍等，我正在处理",
                            "message_id": "client_msg_123",
                        },
                    )

                    assert mock_send_to_role.await_count == 2
                    user_call = mock_send_to_role.await_args_list[0]
                    agent_call = mock_send_to_role.await_args_list[1]

                    assert user_call.args[1] == WSRole.USER
                    assert user_call.args[2]["payload"]["message_id"] == "client_msg_123"
                    assert "is_delivered" not in user_call.args[2]["payload"]

                    assert agent_call.args[1] == WSRole.AGENT
                    assert agent_call.args[2]["payload"]["is_delivered"] is True
                    assert agent_call.args[2]["payload"]["message_id"] == "client_msg_123"
                    services.message_repo.mark_as_delivered.assert_awaited_once_with(["client_msg_123"])
                    mock_broadcast_to_role_global.assert_awaited_once()
                    global_call = mock_broadcast_to_role_global.await_args
                    assert global_call.args[0] == WSRole.AGENT
                    assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
                    assert global_call.args[1]["payload"]["source"] == "agent_message"

    @pytest.mark.anyio
    async def test_handle_agent_send_message_still_syncs_agents_when_user_offline(self):
        """测试用户离线时，客服端仍会收到人工消息，但状态为未送达。"""
        from app.services.websocket.handlers.agent import handle_agent_send_message

        created_at = datetime(2026, 4, 2, 17, 35, 0)
        conn = SimpleNamespace(
            id="conn_789",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            handoff=SimpleNamespace(
                add_human_message=AsyncMock(
                    return_value=SimpleNamespace(id="client_msg_offline", created_at=created_at)
                )
            ),
            message_repo=SimpleNamespace(
                mark_as_delivered=AsyncMock(return_value=0),
            ),
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(side_effect=[0, 1]),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_role_global",
                    new=AsyncMock(return_value=1),
                ) as mock_broadcast_to_role_global:
                    await handle_agent_send_message(
                        conn,
                        WSAction.CLIENT_AGENT_SEND_MESSAGE,
                        {
                            "content": "用户当前离线，先留言",
                            "message_id": "client_msg_offline",
                        },
                    )

                    assert mock_send_to_role.await_count == 2
                    agent_call = mock_send_to_role.await_args_list[1]
                    assert agent_call.args[1] == WSRole.AGENT
                    assert agent_call.args[2]["payload"]["is_delivered"] is False
                    assert agent_call.args[2]["payload"]["delivered_at"] is None
                    services.message_repo.mark_as_delivered.assert_not_awaited()
                    mock_broadcast_to_role_global.assert_awaited_once()


class TestAgentMessageMutationHandlers:
    """测试客服编辑和撤回消息处理器。"""

    @pytest.mark.anyio
    async def test_handle_agent_withdraw_message_broadcasts_global_queue_change(self):
        """测试撤回最后一条人工消息后会触发客服全局队列刷新。"""
        from app.services.websocket.handlers.agent import handle_agent_withdraw_message

        created_at = datetime.now() - timedelta(minutes=1)
        withdrawn_at = datetime.now()
        conn = SimpleNamespace(
            id="conn_withdraw",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            message_repo=SimpleNamespace(
                get_by_id=AsyncMock(
                    return_value=SimpleNamespace(
                        id="msg_123",
                        conversation_id="conv_123",
                        created_at=created_at,
                        is_withdrawn=False,
                    )
                ),
                withdraw_message=AsyncMock(
                    return_value=SimpleNamespace(
                        id="msg_123",
                        withdrawn_at=withdrawn_at,
                    )
                ),
            )
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_conversation",
                    new=AsyncMock(return_value=1),
                ) as mock_broadcast_to_conversation:
                    with patch(
                        "app.services.websocket.handlers.agent.ws_manager.broadcast_to_role_global",
                        new=AsyncMock(return_value=2),
                    ) as mock_broadcast_to_role_global:
                        await handle_agent_withdraw_message(
                            conn,
                            WSAction.CLIENT_AGENT_WITHDRAW_MESSAGE,
                            {"message_id": "msg_123", "reason": "表述有误"},
                        )

        mock_send_to_role.assert_awaited_once()
        mock_broadcast_to_conversation.assert_awaited_once()
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["source"] == "agent_message_withdrawn"
        assert global_call.args[1]["payload"]["changed_at"] == withdrawn_at.isoformat()

    @pytest.mark.anyio
    async def test_handle_agent_edit_message_broadcasts_global_queue_change(self):
        """测试编辑人工消息后会触发客服全局队列刷新。"""
        from app.services.websocket.handlers.agent import handle_agent_edit_message

        created_at = datetime.now() - timedelta(minutes=1)
        edited_at = datetime.now()
        conn = SimpleNamespace(
            id="conn_edit",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            message_repo=SimpleNamespace(
                get_by_id=AsyncMock(
                    return_value=SimpleNamespace(
                        id="msg_123",
                        conversation_id="conv_123",
                        created_at=created_at,
                        is_withdrawn=False,
                        content="原始话术",
                        role="human_agent",
                    )
                ),
                edit_message=AsyncMock(
                    return_value=SimpleNamespace(
                        id="msg_123",
                        edited_at=edited_at,
                    )
                ),
            )
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_conversation",
                    new=AsyncMock(return_value=1),
                ) as mock_broadcast_to_conversation:
                    with patch(
                        "app.services.websocket.handlers.agent.ws_manager.broadcast_to_role_global",
                        new=AsyncMock(return_value=2),
                    ) as mock_broadcast_to_role_global:
                        await handle_agent_edit_message(
                            conn,
                            WSAction.CLIENT_AGENT_EDIT_MESSAGE,
                            {
                                "message_id": "msg_123",
                                "new_content": "修正后的话术",
                                "regenerate": False,
                            },
                        )

        mock_send_to_role.assert_awaited_once()
        mock_broadcast_to_conversation.assert_awaited_once()
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["source"] == "agent_message_edited"
        assert global_call.args[1]["payload"]["changed_at"] == edited_at.isoformat()


class TestAgentHandoffHandlers:
    """测试客服接入与结束接入处理器。"""

    @pytest.mark.anyio
    async def test_handle_agent_start_handoff_only_notifies_user_event(self):
        """测试客服接入时只补发 handoff 事件，不重复推送会话状态。"""
        from app.services.websocket.handlers.agent import handle_agent_start_handoff

        conn = SimpleNamespace(
            id="conn_start",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            complaint_handoff=SimpleNamespace(
                accept_handoff=AsyncMock(return_value={"success": True})
            )
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_conversation",
                    new=AsyncMock(return_value=0),
                ) as mock_broadcast:
                    await handle_agent_start_handoff(
                        conn,
                        WSAction.CLIENT_AGENT_START_HANDOFF,
                        {"reason": "用户要求人工处理"},
                    )

        services.complaint_handoff.accept_handoff.assert_awaited_once_with(
            conversation_id="conv_123",
            operator="agent_a",
            reason="用户要求人工处理",
        )
        mock_send_to_role.assert_awaited_once()
        send_call = mock_send_to_role.await_args
        assert send_call.args[0] == "conv_123"
        assert send_call.args[1] == WSRole.USER
        assert send_call.args[2]["action"] == WSAction.SERVER_HANDOFF_STARTED
        mock_broadcast.assert_not_awaited()

    @pytest.mark.anyio
    async def test_handle_agent_end_handoff_only_notifies_user_event(self):
        """测试客服结束接入时只补发结束事件，不重复推送会话状态。"""
        from app.services.websocket.handlers.agent import handle_agent_end_handoff

        conn = SimpleNamespace(
            id="conn_end",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            complaint_handoff=SimpleNamespace(
                finish_handoff=AsyncMock(return_value={"success": True})
            )
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.agent.ws_manager.broadcast_to_conversation",
                    new=AsyncMock(return_value=0),
                ) as mock_broadcast:
                    await handle_agent_end_handoff(
                        conn,
                        WSAction.CLIENT_AGENT_END_HANDOFF,
                        {"summary": "已完成赔付说明"},
                    )

        services.complaint_handoff.finish_handoff.assert_awaited_once_with(
            conversation_id="conv_123",
            operator="agent_a",
            summary="已完成赔付说明",
        )
        mock_send_to_role.assert_awaited_once()
        send_call = mock_send_to_role.await_args
        assert send_call.args[0] == "conv_123"
        assert send_call.args[1] == WSRole.USER
        assert send_call.args[2]["action"] == WSAction.SERVER_HANDOFF_ENDED
        mock_broadcast.assert_not_awaited()

    @pytest.mark.anyio
    async def test_handle_agent_transfer_uses_transfer_service(self):
        """测试客服转接会走专门的 transfer 服务，而不是复用 accept。"""
        from app.services.websocket.handlers.agent import handle_agent_transfer

        conn = SimpleNamespace(
            id="conn_transfer",
            identity="agent_a",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            complaint_handoff=SimpleNamespace(
                transfer_handoff=AsyncMock(return_value={"success": True})
            )
        )

        with patch(
            "app.services.websocket.handlers.agent.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.agent.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                await handle_agent_transfer(
                    conn,
                    WSAction.CLIENT_AGENT_TRANSFER,
                    {"target_agent_id": "agent_b", "reason": "赔付场景需专员接手"},
                )

        services.complaint_handoff.transfer_handoff.assert_awaited_once_with(
            conversation_id="conv_123",
            operator="agent_b",
            reason="转接自 agent_a: 赔付场景需专员接手",
        )
        mock_send_to_role.assert_awaited_once()
        send_call = mock_send_to_role.await_args
        assert send_call.args[0] == "conv_123"
        assert send_call.args[1] == WSRole.USER
        assert send_call.args[2]["action"] == WSAction.SERVER_HANDOFF_STARTED
