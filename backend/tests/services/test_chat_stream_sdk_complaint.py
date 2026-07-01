"""ChatStreamOrchestratorSDK 投诉前奏事件测试

测试 complaint 初始事件能被正确插入到 meta.start 后面，并保持 seq 顺序稳定。
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from langgraph_agent_kit import StreamEventType
from langgraph_agent_kit.core.context import ChatContext


class FakeAgentService:
    """模拟 AgentService，用于输出固定 domain events。"""

    def __init__(self, events: list[tuple[str, dict[str, Any]]] | None = None):
        """初始化模拟 AgentService。

        Args:
            events: 需要按顺序发送给 emitter 的 domain events。
        """
        self._events = events or []

    async def chat_emit(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str,
        context: ChatContext,
        agent_id: str | None = None,
    ) -> None:
        """把预设 domain events 依次发给编排器。"""
        del message, conversation_id, user_id, agent_id
        for evt_type, payload in self._events:
            await context.emitter.aemit(evt_type, payload)
        await context.emitter.aemit("__end__", None)


class FakeConversationService:
    """模拟 ConversationService，避免真实落库。"""

    async def add_message(self, **kwargs: Any) -> None:
        """接收 assistant message 落库调用，但不执行真实数据库写入。"""
        del kwargs


async def run_orchestrator_with_initial_events(
    *,
    domain_events: list[tuple[str, dict[str, Any]]],
    initial_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """运行 SDK 编排器并收集全部输出事件。"""
    from app.services.chat_stream_sdk import ChatStreamOrchestratorSDK

    orchestrator = ChatStreamOrchestratorSDK(
        conversation_service=FakeConversationService(),
        agent_service=FakeAgentService(domain_events),
        conversation_id="conv_123",
        user_id="user_123",
        user_message="订单还没处理",
        user_message_id="msg_123",
        assistant_message_id="assistant_123",
        initial_events=initial_events,
        db=None,
    )

    collected: list[dict[str, Any]] = []

    async def collect() -> None:
        """收集编排器产生的全部事件。"""
        async for event in orchestrator.run():
            collected.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))

    await asyncio.wait_for(collect(), timeout=10)
    return collected


@pytest.mark.anyio
class TestChatStreamOrchestratorSDKComplaintPrelude:
    """测试 complaint 前奏事件注入。"""

    async def test_initial_events_are_emitted_after_meta_start(self):
        """测试 complaint 事件会插入到 meta.start 之后。"""
        events = await run_orchestrator_with_initial_events(
            domain_events=[],
            initial_events=[
                {
                    "type": "complaint.ticket.created",
                    "payload": {"ticket": {"id": "ticket_123"}},
                }
            ],
        )

        assert events[0]["type"] == "meta.start"
        assert events[1]["type"] == "complaint.ticket.created"
        assert events[1]["payload"]["ticket"]["id"] == "ticket_123"

    async def test_initial_events_shift_following_seq_numbers(self):
        """测试 complaint 事件插入后，后续事件 seq 仍保持递增。"""
        events = await run_orchestrator_with_initial_events(
            domain_events=[
                (StreamEventType.ASSISTANT_DELTA.value, {"delta": "好"}),
                (StreamEventType.ASSISTANT_FINAL.value, {"content": "好"}),
            ],
            initial_events=[
                {
                    "type": "complaint.ticket.merged",
                    "payload": {"ticket_id": "ticket_123"},
                }
            ],
        )

        seqs = [event["seq"] for event in events if event.get("seq") is not None]
        assert seqs == sorted(seqs)
        assert events[0]["type"] == "meta.start"
        assert events[1]["type"] == "complaint.ticket.merged"
        assert events[2]["type"] == "assistant.delta"
