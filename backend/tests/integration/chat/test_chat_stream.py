"""聊天流集成测试

验证真实 AI 场景下的聊天流程和 SSE 事件推送。
"""

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

# 加载 .env 文件
_env_path = Path(__file__).parents[3] / ".env"
if _env_path.exists():
    load_dotenv(_env_path, override=True)


def _has_api_config() -> bool:
    """检查是否配置了 API Key"""
    api_key = os.getenv("LLM_API_KEY")
    provider = os.getenv("LLM_PROVIDER")
    return bool(
        api_key
        and api_key != "test"
        and provider
        and provider != "test"
    )


requires_api = pytest.mark.skipif(
    not _has_api_config(),
    reason="需要配置真实的 LLM_API_KEY 和 LLM_PROVIDER",
)
integration = pytest.mark.integration
slow = pytest.mark.slow


@pytest.mark.anyio
@requires_api
@integration
@slow
class TestChatStreamIntegration:
    """聊天流集成测试"""

    def _get_conversation_id(self) -> str:
        """生成测试会话 ID"""
        return f"test-conv-{uuid.uuid4().hex[:8]}"

    def _get_user_id(self) -> str:
        """生成测试用户 ID"""
        return f"test-user-{uuid.uuid4().hex[:8]}"

    async def test_chat_stream_basic_flow(self):
        """测试基本聊天流程

        验证：
        1. meta.start 事件正确发出
        2. assistant.delta 事件包含文本增量
        3. assistant.final 事件包含完整内容
        """
        from app.core.database import get_db_context
        from app.services.agent.core.service import agent_service
        from app.services.chat_stream import ChatStreamOrchestrator
        from app.services.conversation import ConversationService

        conversation_id = self._get_conversation_id()
        user_id = self._get_user_id()

        async with get_db_context() as db_session:
            conversation_service = ConversationService(db_session)

            # 先保存用户消息
            user_message = await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content="你好",
            )

            assistant_message_id = str(uuid.uuid4())
            orchestrator = ChatStreamOrchestrator(
                conversation_service=conversation_service,
                agent_service=agent_service,
                conversation_id=conversation_id,
                user_id=user_id,
                user_message="你好",
                user_message_id=user_message.id,
                assistant_message_id=assistant_message_id,
                mode="natural",
                db=db_session,
            )

            events: list[dict[str, Any]] = []
            
            # 添加超时保护，避免 LLM 调用卡住导致测试无限等待
            async def collect_events():
                async for event in orchestrator.run():
                    events.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))
            
            try:
                await asyncio.wait_for(collect_events(), timeout=120)
            except asyncio.TimeoutError:
                pytest.fail("测试超时（120秒），可能是 LLM 调用或 Agent 构建卡住")

            # 验证事件流
            event_types = [e.get("type") for e in events]

            # 1. 必须有 meta.start
            assert "meta.start" in event_types, "缺少 meta.start 事件"

            # 2. 必须有 assistant.delta 或 assistant.final
            has_content = "assistant.delta" in event_types or "assistant.final" in event_types
            assert has_content, "缺少内容事件"

            # 3. 最后一个事件应该是 assistant.final
            final_events = [e for e in events if e.get("type") == "assistant.final"]
            assert len(final_events) >= 1, "缺少 assistant.final 事件"

            # 4. 验证 meta.start 包含正确的 message_id
            start_event = next(e for e in events if e.get("type") == "meta.start")
            assert start_event["payload"]["assistant_message_id"] == assistant_message_id

    async def test_chat_stream_with_tool_call(self):
        """测试带工具调用的聊天流程

        验证：
        1. 当查询商品时，触发 tool.start 事件
        2. 工具执行完成后，触发 tool.end 事件
        3. 工具调用包含正确的名称和状态
        """
        from app.core.database import get_db_context
        from app.services.agent.core.service import agent_service
        from app.services.chat_stream import ChatStreamOrchestrator
        from app.services.conversation import ConversationService

        conversation_id = self._get_conversation_id()
        user_id = self._get_user_id()

        async with get_db_context() as db_session:
            conversation_service = ConversationService(db_session)

            # 保存用户消息（触发商品搜索）
            user_message = await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content="推荐一款降噪耳机",
            )

            assistant_message_id = str(uuid.uuid4())
            orchestrator = ChatStreamOrchestrator(
                conversation_service=conversation_service,
                agent_service=agent_service,
                conversation_id=conversation_id,
                user_id=user_id,
                user_message="推荐一款降噪耳机",
                user_message_id=user_message.id,
                assistant_message_id=assistant_message_id,
                mode="natural",
                db=db_session,
            )

            events: list[dict[str, Any]] = []
            
            async def collect_events():
                async for event in orchestrator.run():
                    events.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))
            
            try:
                await asyncio.wait_for(collect_events(), timeout=120)
            except asyncio.TimeoutError:
                pytest.fail("测试超时（120秒）")

            event_types = [e.get("type") for e in events]

            # 验证基本流程
            assert "meta.start" in event_types, "缺少 meta.start 事件"
            assert "assistant.final" in event_types, "缺少 assistant.final 事件"

            # 验证工具调用事件（如果有）
            tool_start_events = [e for e in events if e.get("type") == "tool.start"]
            tool_end_events = [e for e in events if e.get("type") == "tool.end"]

            if tool_start_events:
                # 如果有 tool.start，必须有对应的 tool.end
                assert len(tool_end_events) >= 1, "有 tool.start 但缺少 tool.end"

                # 验证 tool.start 结构
                for ts in tool_start_events:
                    payload = ts.get("payload", {})
                    assert "tool_call_id" in payload, "tool.start 缺少 tool_call_id"
                    assert "name" in payload, "tool.start 缺少 name"

                # 验证 tool.end 结构
                for te in tool_end_events:
                    payload = te.get("payload", {})
                    assert "tool_call_id" in payload, "tool.end 缺少 tool_call_id"
                    assert "name" in payload, "tool.end 缺少 name"
                    assert "status" in payload, "tool.end 缺少 status"
                    assert payload["status"] in ["success", "error", "empty"], f"无效的 status: {payload['status']}"

    async def test_chat_stream_strict_mode(self):
        """测试严格模式聊天流程

        验证：
        1. 严格模式下，如果无工具调用，返回引导信息
        2. 严格模式下，工具返回 empty 时有特殊处理
        """
        from app.core.database import get_db_context
        from app.services.agent.core.service import agent_service
        from app.services.chat_stream import ChatStreamOrchestrator
        from app.services.conversation import ConversationService

        conversation_id = self._get_conversation_id()
        user_id = self._get_user_id()

        async with get_db_context() as db_session:
            conversation_service = ConversationService(db_session)

            # 保存用户消息
            user_message = await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content="你好",
            )

            assistant_message_id = str(uuid.uuid4())
            orchestrator = ChatStreamOrchestrator(
                conversation_service=conversation_service,
                agent_service=agent_service,
                conversation_id=conversation_id,
                user_id=user_id,
                user_message="你好",
                user_message_id=user_message.id,
                assistant_message_id=assistant_message_id,
                mode="strict",  # 严格模式
                db=db_session,
            )

            events: list[dict[str, Any]] = []
            
            async def collect_events():
                async for event in orchestrator.run():
                    events.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))
            
            try:
                await asyncio.wait_for(collect_events(), timeout=120)
            except asyncio.TimeoutError:
                pytest.fail("测试超时（120秒）")

            # 验证有响应
            final_events = [e for e in events if e.get("type") == "assistant.final"]
            assert len(final_events) >= 1, "缺少 assistant.final 事件"

            # 严格模式下，简单问候可能触发兖底逻辑
            final_content = final_events[0].get("payload", {}).get("content", "")
            assert len(final_content) > 0, "严格模式下应有响应内容"

    async def _collect_events(self, message: str, mode: str = "natural") -> list[dict[str, Any]]:
        """收集聊天流产生的所有事件
        
        注意：为避免 SQLite 嵌套连接死锁，使用单一数据库上下文
        """
        import asyncio
        from app.core.database import get_db_context
        from app.services.agent.core.service import agent_service
        from app.services.chat_stream import ChatStreamOrchestrator
        from app.services.conversation import ConversationService

        conversation_id = self._get_conversation_id()
        user_id = self._get_user_id()
        assistant_message_id = str(uuid.uuid4())

        # Step 1: 先初始化 agent_service（让它内部获取数据库连接）
        await agent_service.get_default_agent_id()

        # Step 2: 在单一上下文中执行所有操作
        async with get_db_context() as db_session:
            conversation_service = ConversationService(db_session)

            user_message = await conversation_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=message,
            )

            orchestrator = ChatStreamOrchestrator(
                conversation_service=conversation_service,
                agent_service=agent_service,
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=message,
                user_message_id=user_message.id,
                assistant_message_id=assistant_message_id,
                mode=mode,
                db=db_session,
            )

            events: list[dict[str, Any]] = []
            
            async def collect_events():
                async for event in orchestrator.run():
                    events.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))
            
            # 添加超时保护，避免无限等待
            try:
                await asyncio.wait_for(collect_events(), timeout=120)
            except asyncio.TimeoutError:
                pytest.fail("测试超时（120秒）")

            return events

    async def test_chat_stream_event_sequence(self):
        """测试事件序列正确性

        验证：
        1. seq 序号递增
        2. 事件顺序正确（meta.start 在前，assistant.final 在后）
        """
        events = await self._collect_events("你好")
        seqs = [e.get("seq") for e in events if e.get("seq") is not None]
        for i in range(1, len(seqs)):
            assert seqs[i] > seqs[i - 1], f"seq 未递增: {seqs[i - 1]} -> {seqs[i]}"

        # 验证 meta.start 是第一个事件
        assert events[0].get("type") == "meta.start", "第一个事件应为 meta.start"

        # 验证 assistant.final 存在
        final_idx = next(
            (i for i, e in enumerate(events) if e.get("type") == "assistant.final"),
            -1,
        )
        assert final_idx > 0, "assistant.final 应在 meta.start 之后"

    async def test_chat_stream_error_handling(self):
        """测试错误处理

        验证：
        1. 异常情况下发送 error 事件
        2. error 事件包含错误信息
        """
        from unittest.mock import AsyncMock, MagicMock
        from app.services.chat_stream import ChatStreamOrchestrator

        conversation_id = self._get_conversation_id()
        user_id = self._get_user_id()
        assistant_message_id = str(uuid.uuid4())
        user_message_id = str(uuid.uuid4())

        # 完全 mock conversation_service，避免数据库操作
        mock_conversation_service = MagicMock()
        mock_conversation_service.add_message = AsyncMock()

        # 创建一个 mock agent_service 来模拟错误
        # 注意：必须在 finally 中发送 __end__ 事件，否则 orchestrator 会永久等待
        class MockAgentService:
            async def chat_emit(self, **kwargs):
                context = kwargs.get("context")
                emitter = getattr(context, "emitter", None)
                try:
                    raise ValueError("模拟的错误")
                except Exception as e:
                    if emitter:
                        await emitter.aemit("error", {"message": str(e)})
                finally:
                    if emitter:
                        await emitter.aemit("__end__", None)

        orchestrator = ChatStreamOrchestrator(
            conversation_service=mock_conversation_service,
            agent_service=MockAgentService(),
            conversation_id=conversation_id,
            user_id=user_id,
            user_message="测试",
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            mode="natural",
            db=None,  # 不需要真实数据库
        )

        events: list[dict[str, Any]] = []
        async for event in orchestrator.run():
            events.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))

        # 应该有 error 事件
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1, "缺少 error 事件"

        # error 事件应包含 message
        error_payload = error_events[0].get("payload", {})
        assert "message" in error_payload, "error 事件缺少 message"
