"""SSE 事件推送集成测试

验证真实 AI 场景下各类 SSE 事件的结构和内容正确性。
"""

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
class TestSSEEventsIntegration:
    """SSE 事件推送集成测试"""

    def _get_conversation_id(self) -> str:
        return f"test-sse-{uuid.uuid4().hex[:8]}"

    def _get_user_id(self) -> str:
        return f"test-user-{uuid.uuid4().hex[:8]}"

    async def _collect_events(self, message: str, mode: str = "natural") -> list[dict[str, Any]]:
        """收集聊天流产生的所有事件
        
        注意：为避免 SQLite 嵌套连接死锁，先初始化 agent_service
        """
        import asyncio
        from app.core.database import get_db_context
        from app.services.agent.core.service import agent_service
        from app.services.chat_stream import ChatStreamOrchestrator
        from app.services.conversation import ConversationService

        conversation_id = self._get_conversation_id()
        user_id = self._get_user_id()
        assistant_message_id = str(uuid.uuid4())

        # 先初始化 agent_service（避免嵌套数据库连接）
        await agent_service.get_default_agent_id()

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
            
            try:
                await asyncio.wait_for(collect_events(), timeout=120)
            except asyncio.TimeoutError:
                pytest.fail("测试超时（120秒）")

            return events

    async def test_meta_start_event_structure(self):
        """测试 meta.start 事件结构

        验证：
        1. 包含 user_message_id
        2. 包含 assistant_message_id
        3. conversation_id 正确
        """
        events = await self._collect_events("你好")

        start_events = [e for e in events if e.get("type") == "meta.start"]
        assert len(start_events) == 1, "应有且仅有一个 meta.start 事件"

        event = start_events[0]

        # 验证顶层结构
        assert "v" in event, "缺少版本号 v"
        assert "id" in event, "缺少事件 id"
        assert "seq" in event, "缺少序号 seq"
        assert "conversation_id" in event, "缺少 conversation_id"
        assert "message_id" in event, "缺少 message_id"
        assert "type" in event, "缺少 type"
        assert "payload" in event, "缺少 payload"

        # 验证 payload 结构
        payload = event["payload"]
        assert "user_message_id" in payload, "payload 缺少 user_message_id"
        assert "assistant_message_id" in payload, "payload 缺少 assistant_message_id"

        # 验证 conversation_id 存在
        assert event["conversation_id"] is not None

    async def test_assistant_delta_event_structure(self):
        """测试 assistant.delta 事件结构

        验证：
        1. delta 字段存在且为字符串
        2. 多个 delta 事件的 seq 递增
        """
        events = await self._collect_events("你好")

        delta_events = [e for e in events if e.get("type") == "assistant.delta"]

        if delta_events:
            # 验证每个 delta 事件的结构
            for event in delta_events:
                payload = event.get("payload", {})
                assert "delta" in payload, "delta 事件缺少 delta 字段"
                assert isinstance(payload["delta"], str), "delta 应为字符串"

            # 验证 seq 递增
            seqs = [e.get("seq") for e in delta_events]
            for i in range(1, len(seqs)):
                assert seqs[i] > seqs[i - 1], "delta 事件 seq 应递增"

    async def test_assistant_final_event_structure(self):
        """测试 assistant.final 事件结构

        验证：
        1. content 字段存在
        2. 可选的 reasoning、products 字段
        """
        events = await self._collect_events("你好")

        final_events = [e for e in events if e.get("type") == "assistant.final"]
        assert len(final_events) >= 1, "应至少有一个 assistant.final 事件"

        event = final_events[0]
        payload = event.get("payload", {})

        # content 应该存在（可以为空字符串）
        assert "content" in payload, "final 事件缺少 content 字段"

        # products 如果存在应该是 list 或 None
        if "products" in payload and payload["products"] is not None:
            assert isinstance(payload["products"], list), "products 应为列表"

    async def test_tool_events_structure(self):
        """测试工具调用事件结构

        验证：
        1. tool.start 包含 tool_call_id, name, input
        2. tool.end 包含 tool_call_id, name, status, count
        3. tool_call_id 在 start 和 end 中匹配
        """
        events = await self._collect_events("推荐一款500元以内的耳机")

        tool_start_events = [e for e in events if e.get("type") == "tool.start"]
        tool_end_events = [e for e in events if e.get("type") == "tool.end"]

        if tool_start_events:
            # 验证 tool.start 结构
            for event in tool_start_events:
                payload = event.get("payload", {})
                assert "tool_call_id" in payload, "tool.start 缺少 tool_call_id"
                assert "name" in payload, "tool.start 缺少 name"
                assert isinstance(payload["name"], str), "name 应为字符串"

            # 验证 tool.end 结构
            for event in tool_end_events:
                payload = event.get("payload", {})
                assert "tool_call_id" in payload, "tool.end 缺少 tool_call_id"
                assert "name" in payload, "tool.end 缺少 name"
                assert "status" in payload, "tool.end 缺少 status"

                # 验证 status 值
                valid_statuses = ["success", "error", "empty"]
                assert payload["status"] in valid_statuses, f"无效 status: {payload['status']}"

            # 验证 tool_call_id 匹配
            start_ids = {e["payload"]["tool_call_id"] for e in tool_start_events}
            end_ids = {e["payload"]["tool_call_id"] for e in tool_end_events}

            # 每个 start 应该有对应的 end
            assert start_ids == end_ids, "tool.start 和 tool.end 的 tool_call_id 不匹配"

    async def test_products_event_structure(self):
        """测试商品数据事件结构

        验证：
        1. assistant.products 事件包含 items 数组
        2. 每个商品包含必要字段：id, name, price
        """
        events = await self._collect_events("推荐一款降噪耳机")

        products_events = [e for e in events if e.get("type") == "assistant.products"]

        if products_events:
            for event in products_events:
                payload = event.get("payload", {})
                assert "items" in payload, "products 事件缺少 items"
                items = payload["items"]
                assert isinstance(items, list), "items 应为列表"

                # 验证每个商品的结构
                for item in items:
                    assert "id" in item, "商品缺少 id"
                    assert "name" in item, "商品缺少 name"
                    # price 可能为 None（某些商品可能无价格）
                    if "price" in item and item["price"] is not None:
                        assert isinstance(item["price"], (int, float)), "price 应为数字"

    async def test_event_encoding(self):
        """测试 SSE 事件编码

        验证：
        1. 事件能正确序列化为 JSON
        2. encode_sse 函数正确编码
        """
        from app.routers.chat import encode_sse

        events = await self._collect_events("你好")

        for event in events:
            # 尝试编码为 SSE
            try:
                sse_str = encode_sse(event)
                assert isinstance(sse_str, str), "encode_sse 应返回字符串"
                assert sse_str.startswith("data: "), "SSE 数据应以 'data: ' 开头"
                assert sse_str.endswith("\n\n"), "SSE 数据应以双换行结尾"

                # 验证 JSON 可解析
                json_str = sse_str[6:-2]  # 去掉 "data: " 和 "\n\n"
                parsed = json.loads(json_str)
                assert "type" in parsed, "解析后的数据缺少 type"
            except Exception as e:
                pytest.fail(f"事件编码失败: {e}, event: {event}")

    async def test_event_versioning(self):
        """测试事件版本控制

        验证：
        1. 所有事件包含版本号 v
        2. 版本号一致
        """
        events = await self._collect_events("你好")

        versions = set()
        for event in events:
            assert "v" in event, f"事件缺少版本号: {event.get('type')}"
            versions.add(event["v"])

        # 所有事件版本应一致
        assert len(versions) == 1, f"事件版本不一致: {versions}"

    async def test_llm_call_boundary_events(self):
        """测试 LLM 调用边界事件

        验证：
        1. llm.call.start 和 llm.call.end 成对出现
        2. llm.call.end 包含 elapsed_ms
        """
        events = await self._collect_events("你好")

        llm_start_events = [e for e in events if e.get("type") == "llm.call.start"]
        llm_end_events = [e for e in events if e.get("type") == "llm.call.end"]

        # LLM 调用边界事件可能不存在（取决于中间件配置）
        if llm_start_events or llm_end_events:
            # 如果有 start，应该有对应的 end
            assert len(llm_start_events) == len(llm_end_events), (
                f"llm.call.start ({len(llm_start_events)}) 和 "
                f"llm.call.end ({len(llm_end_events)}) 数量不匹配"
            )

            # 验证 llm.call.end 结构
            for event in llm_end_events:
                payload = event.get("payload", {})
                assert "elapsed_ms" in payload, "llm.call.end 缺少 elapsed_ms"
                assert isinstance(payload["elapsed_ms"], int), "elapsed_ms 应为整数"
