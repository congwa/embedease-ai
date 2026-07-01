"""投诉聊天路由测试

本文件的业务职责，是验证 `/api/v1/chat` 已经能在 AI 客诉模式和人工模式下
分别走正确的业务主链路，而不是一律退回普通聊天逻辑。
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintTriageResult,
    IssueContinuity,
    PlannerDecision,
    ReviewDecision,
    TicketStreamSummary,
)
from app.services.complaint.orchestrator import ComplaintRunContext


def build_run_context() -> ComplaintRunContext:
    """构造基础 complaint run context，服务于聊天路由测试。"""
    return ComplaintRunContext(
        conversation_id="conv_123",
        user_id="user_123",
        user_message_id="msg_123",
        ticket_id="ticket_123",
        ticket_summary=TicketStreamSummary(
            id="ticket_123",
            status="in_progress",
            primary_issue_tag="refund_request",
        ),
        triage_result=ComplaintTriageResult(
            primary_issue_tag="refund_request",
            priority_level="urgent",
            risk_level="medium",
            sentiment="negative",
            severity="major",
            emotional_intensity="medium",
            continuity=IssueContinuity.SAME_ISSUE,
            requested_human=False,
            missing_slots=[],
            extracted_slots={},
            summary="主问题=refund_request，风险=medium，情绪=negative",
        ),
        planner_decision=PlannerDecision(
            assigned_agent_tag="resolution_execution_agent",
            task_type="resolution",
            goal="推进退款问题处理",
            success_criteria=["用户知道下一步动作"],
            should_handoff=False,
            next_node_key="resolution",
            reasoning="当前信息已经足够进入处理推进",
        ),
        review_decision=ReviewDecision(
            status=ComplaintReviewStatus.PASSED,
            score=88,
            risk_level="medium",
            reasons=[],
            should_handoff=False,
        ),
        assistant_candidate_content="已为您记录退款问题，正在继续推进。",
        should_emit_assistant_final=True,
        handoff_result=None,
        pre_stream_events=[
            {
                "type": "complaint.ticket.created",
                "payload": {"ticket": {"id": "ticket_123"}},
            }
        ],
        post_stream_events=[],
        assistant_extra_metadata={},
    )


def build_request() -> ChatRequest:
    """构造聊天请求对象，服务于路由行为测试。"""
    return ChatRequest(
        user_id="user_123",
        conversation_id="conv_123",
        message="我的退款一直没处理",
    )


class FakeRequest:
    """模拟 FastAPI Request。

    这个对象只提供聊天路由真正依赖的 `is_disconnected` 能力，避免测试引入真实 ASGI 环境。
    """

    async def is_disconnected(self) -> bool:
        """始终保持连接，以便完整收集 SSE 输出。"""
        return False


def build_db_context(*sessions: object):
    """构造依次返回固定 session 的异步上下文工厂。"""
    iterator = iter(sessions)

    @asynccontextmanager
    async def _context():
        yield next(iterator)

    return _context


async def collect_stream_body(response) -> str:
    """收集 StreamingResponse 的全部输出文本。"""
    body_chunks: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            body_chunks.append(chunk.decode("utf-8"))
        else:
            body_chunks.append(chunk)
    return "".join(body_chunks)


def close_background_task(coro):
    """关闭测试中创建的后台协程。

    这个方法用于避免 `notify_new_message()` 在单测里真的启动后台任务。
    """
    coro.close()
    return MagicMock()


@pytest.mark.anyio
class TestChatComplaintRouter:
    """测试 chat 路由在投诉模式下的关键分支。"""

    async def test_chat_route_uses_complaint_stream_in_ai_mode(self):
        """测试 AI 模式下会走 complaint orchestrator 和 complaint stream。"""
        from app.routers.chat import chat

        outer_db = MagicMock()
        stream_db = MagicMock()
        outer_conversation_service = MagicMock()
        outer_conversation_service.add_message = AsyncMock(
            return_value=MagicMock(id="msg_123")
        )
        stream_conversation_service = MagicMock()
        complaint_run_context = build_run_context()

        async def fake_stream():
            yield {"type": "meta.start", "payload": {"assistant_message_id": "assistant_123"}}
            yield {"type": "complaint.ticket.created", "payload": {"ticket": {"id": "ticket_123"}}}
            yield {"type": "assistant.final", "payload": {"content": "已为您记录退款问题，正在继续推进。"}}

        with patch(
            "app.routers.chat.get_db_context",
            new=build_db_context(outer_db, stream_db),
        ), patch(
            "app.routers.chat.ConversationService",
            side_effect=[outer_conversation_service, stream_conversation_service],
        ), patch(
            "app.routers.chat.HandoffService"
        ) as MockHandoffService, patch(
            "app.routers.chat.ComplaintConversationOrchestrator"
        ) as MockComplaintOrchestrator, patch(
            "app.routers.chat.ComplaintChatStreamOrchestrator"
        ) as MockComplaintStream, patch(
            "app.routers.chat.asyncio.create_task",
            side_effect=close_background_task,
        ), patch(
            "app.routers.chat.encode_sse",
            side_effect=lambda event: json.dumps(event, ensure_ascii=False),
        ):
            mock_handoff_service = MockHandoffService.return_value
            mock_handoff_service.get_handoff_state = AsyncMock(return_value="ai")

            mock_complaint_orchestrator = MockComplaintOrchestrator.return_value
            mock_complaint_orchestrator.handle_user_message = AsyncMock(
                return_value=complaint_run_context
            )

            mock_complaint_stream = MockComplaintStream.return_value
            mock_complaint_stream.run = MagicMock(return_value=fake_stream())

            response = await chat(build_request(), FakeRequest())
            body = await collect_stream_body(response)

            assert "complaint.ticket.created" in body
            assert "assistant.final" in body
            mock_complaint_orchestrator.handle_user_message.assert_awaited_once()
            MockComplaintStream.assert_called_once()

    async def test_chat_route_skips_complaint_orchestrator_in_human_mode(self):
        """测试人工模式下不会再触发 complaint orchestrator。"""
        from app.routers.chat import chat

        outer_db = MagicMock()
        outer_conversation_service = MagicMock()
        outer_conversation_service.add_message = AsyncMock(
            return_value=MagicMock(id="msg_123")
        )

        with patch(
            "app.routers.chat.get_db_context",
            new=build_db_context(outer_db),
        ), patch(
            "app.routers.chat.ConversationService",
            return_value=outer_conversation_service,
        ), patch(
            "app.routers.chat.HandoffService"
        ) as MockHandoffService, patch(
            "app.routers.chat.ComplaintConversationOrchestrator"
        ) as MockComplaintOrchestrator, patch(
            "app.routers.chat.asyncio.create_task",
            side_effect=close_background_task,
        ), patch(
            "app.routers.chat.encode_sse",
            side_effect=lambda event: json.dumps(event, ensure_ascii=False),
        ), patch(
            "app.services.websocket.manager.ws_manager.send_to_role",
            new=AsyncMock(return_value=True),
        ):
            mock_handoff_service = MockHandoffService.return_value
            mock_handoff_service.get_handoff_state = AsyncMock(return_value="human")

            mock_complaint_orchestrator = MockComplaintOrchestrator.return_value
            mock_complaint_orchestrator.handle_user_message = AsyncMock()

            response = await chat(build_request(), FakeRequest())
            body = await collect_stream_body(response)

            assert "support.human_mode" in body
            assert "\"mode\": \"human\"" in body
            mock_complaint_orchestrator.handle_user_message.assert_not_called()
