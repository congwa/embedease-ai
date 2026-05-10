"""ChatStreamOrchestratorSDK 单元测试

测试 SDK v0.2.0 Orchestrator 集成：
- AgentRunner 委托
- ContentAggregator 自动聚合
- on_stream_end 落库钩子
- 构造函数兼容性
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from langgraph_agent_kit import StreamEventType
from langgraph_agent_kit.core.context import ChatContext

# 所有 async 测试的超时（秒）
ASYNC_TIMEOUT = 10


# ==================== Fixtures ====================


class FakeAgentService:
    """模拟 AgentService，通过 emitter 发送预定义事件序列"""

    def __init__(self, events: list[tuple[str, dict[str, Any]]] | None = None):
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
        emitter = context.emitter
        for evt_type, payload in self._events:
            await emitter.aemit(evt_type, payload)
        await emitter.aemit("__end__", None)


class FakeConversationService:
    """模拟 ConversationService"""

    def __init__(self):
        self.saved_messages: list[dict[str, Any]] = []

    async def add_message(self, **kwargs: Any) -> None:
        self.saved_messages.append(kwargs)


async def _run_orchestrator(
    events: list[tuple[str, dict[str, Any]]],
    message: str = "你好",
) -> tuple[list[dict], FakeConversationService]:
    """辅助：运行编排器并收集所有 StreamEvent（带超时保护）"""
    from app.services.chat_stream_sdk import ChatStreamOrchestratorSDK

    conv_service = FakeConversationService()
    agent_service = FakeAgentService(events)

    orchestrator = ChatStreamOrchestratorSDK(
        conversation_service=conv_service,
        agent_service=agent_service,
        conversation_id="test-conv-1",
        user_id="test-user-1",
        user_message=message,
        user_message_id="umsg-1",
        assistant_message_id="amsg-1",
        db=None,
    )

    collected: list[dict] = []

    async def _collect():
        async for event in orchestrator.run():
            collected.append(
                event.model_dump() if hasattr(event, "model_dump") else dict(event)
            )

    await asyncio.wait_for(_collect(), timeout=ASYNC_TIMEOUT)
    return collected, conv_service


# ==================== Tests ====================


@pytest.mark.anyio
class TestChatStreamOrchestratorSDK:
    """测试 SDK v0.2.0 编排器"""

    async def test_meta_start_emitted(self):
        """meta.start 事件应自动发送"""
        events, _ = await _run_orchestrator([])

        start_events = [e for e in events if e.get("type") == "meta.start"]
        assert len(start_events) == 1
        payload = start_events[0]["payload"]
        assert payload["user_message_id"] == "umsg-1"
        assert payload["assistant_message_id"] == "amsg-1"

    async def test_assistant_delta_forwarded(self):
        """assistant.delta 事件应正确转发"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "你"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "好"}),
        ]
        events, _ = await _run_orchestrator(domain_events)

        deltas = [e for e in events if e.get("type") == "assistant.delta"]
        assert len(deltas) == 2
        assert deltas[0]["payload"]["delta"] == "你"
        assert deltas[1]["payload"]["delta"] == "好"

    async def test_content_aggregated_and_saved(self):
        """ContentAggregator 应聚合内容并在 on_stream_end 落库"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "推荐"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "这款"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "推荐这款"}),
        ]
        _, conv_service = await _run_orchestrator(domain_events)

        assert len(conv_service.saved_messages) == 1
        saved = conv_service.saved_messages[0]
        assert saved["conversation_id"] == "test-conv-1"
        assert saved["role"] == "assistant"
        assert saved["content"] == "推荐这款"
        assert saved["message_id"] == "amsg-1"

    async def test_reasoning_aggregated(self):
        """推理内容应被聚合并保存到 extra_metadata"""
        domain_events = [
            (StreamEventType.ASSISTANT_REASONING_DELTA.value, {"delta": "思考中..."}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "回复"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "回复", "reasoning": "思考中..."}),
        ]
        _, conv_service = await _run_orchestrator(domain_events)

        saved = conv_service.saved_messages[0]
        assert saved["extra_metadata"] is not None
        assert saved["extra_metadata"]["reasoning"] == "思考中..."

    async def test_tool_calls_tracked(self):
        """工具调用应被追踪并保存"""
        domain_events = [
            (StreamEventType.TOOL_START.value, {
                "tool_call_id": "tc-1",
                "name": "search_products",
                "input": {"query": "耳机"},
            }),
            (StreamEventType.TOOL_END.value, {
                "tool_call_id": "tc-1",
                "name": "search_products",
                "status": "success",
                "output_preview": "找到 5 个结果",
            }),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "找到了"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "找到了"}),
        ]
        _, conv_service = await _run_orchestrator(domain_events)

        saved = conv_service.saved_messages[0]
        assert saved["tool_calls_data"] is not None
        assert len(saved["tool_calls_data"]) == 1
        tc = saved["tool_calls_data"][0]
        assert tc["name"] == "search_products"
        assert tc["status"] == "success"

    async def test_products_aggregated(self):
        """商品数据应被聚合"""
        domain_events = [
            (StreamEventType.ASSISTANT_PRODUCTS.value, {
                "items": [{"id": "p1", "name": "耳机A", "price": 299}],
            }),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "推荐", "products": [{"id": "p1"}]}),
        ]
        _, conv_service = await _run_orchestrator(domain_events)

        saved = conv_service.saved_messages[0]
        assert saved["products"] is not None
        products = json.loads(saved["products"])
        assert len(products) >= 1

    async def test_seq_monotonically_increasing(self):
        """事件序号应单调递增"""
        domain_events = [
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "a"}),
            (StreamEventType.ASSISTANT_DELTA.value, {"delta": "b"}),
            (StreamEventType.ASSISTANT_FINAL.value, {"content": "ab"}),
        ]
        events, _ = await _run_orchestrator(domain_events)

        seqs = [e.get("seq") for e in events if e.get("seq") is not None]
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1], f"seq 不单调递增: {seqs}"


class TestChatStreamOrchestratorSDKSync:
    """同步测试（构造函数、兼容性）"""

    def test_interface_compatible_with_legacy(self):
        """构造函数签名应与 Legacy 版本兼容"""
        from app.services.chat_stream_sdk import ChatStreamOrchestratorSDK

        orchestrator = ChatStreamOrchestratorSDK(
            conversation_service=FakeConversationService(),
            agent_service=FakeAgentService(),
            conversation_id="c1",
            user_id="u1",
            user_message="msg",
            user_message_id="um1",
            assistant_message_id="am1",
            agent_id="agent-123",
            images=[{"id": "img1", "url": "http://localhost:3000/placeholders/product.svg"}],
            db=None,
        )
        assert orchestrator is not None


@pytest.mark.anyio
class TestEmbedEaseAgentRunner:
    """测试 AgentRunner 实现"""

    async def test_delegates_to_agent_service(self):
        """AgentRunner 应正确委托给 agent_service.chat_emit()"""
        from app.services.chat_stream_sdk import EmbedEaseAgentRunner

        mock_agent_service = AsyncMock()
        runner = EmbedEaseAgentRunner(mock_agent_service, agent_id="test-agent")

        mock_context = MagicMock(spec=ChatContext)
        mock_context.conversation_id = "conv-1"
        mock_context.user_id = "user-1"

        await runner.run(message="你好", context=mock_context)

        mock_agent_service.chat_emit.assert_called_once_with(
            message="你好",
            conversation_id="conv-1",
            user_id="user-1",
            context=mock_context,
            agent_id="test-agent",
        )
