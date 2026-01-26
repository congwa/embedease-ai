"""工具调用集成测试

验证真实 AI 场景下各类工具的调用和执行。
"""

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
class TestToolCallsIntegration:
    """工具调用集成测试"""

    def _get_conversation_id(self) -> str:
        return f"test-tool-{uuid.uuid4().hex[:8]}"

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

    def _extract_tool_events(
        self, events: list[dict[str, Any]]
    ) -> tuple[list[dict], list[dict]]:
        """从事件列表中提取工具事件"""
        tool_starts = [e for e in events if e.get("type") == "tool.start"]
        tool_ends = [e for e in events if e.get("type") == "tool.end"]
        return tool_starts, tool_ends

    async def test_search_products_tool(self):
        """测试商品搜索工具 (search_products)

        验证：
        1. 搜索请求触发 search_products 工具
        2. 工具返回商品列表或 empty 状态
        3. 工具执行状态正确
        """
        events = await self._collect_events("帮我找一款降噪耳机")

        tool_starts, tool_ends = self._extract_tool_events(events)

        # 检查是否调用了搜索工具
        search_tool_called = any(
            e["payload"].get("name") == "search_products" for e in tool_starts
        )

        if search_tool_called:
            # 找到对应的 tool.end
            search_ends = [
                e for e in tool_ends
                if e["payload"].get("name") == "search_products"
            ]
            assert len(search_ends) >= 1, "search_products 缺少 tool.end"

            for end_event in search_ends:
                payload = end_event["payload"]
                status = payload.get("status")
                assert status in ["success", "error", "empty"], f"无效状态: {status}"

                if status == "success":
                    # 成功时应有 count（count 可能为 0，表示无匹配结果）
                    assert "count" in payload, "成功时缺少 count"
                    assert payload["count"] >= 0, f"count 应为非负数: {payload['count']}"

    async def test_filter_price_tool(self):
        """测试价格筛选工具 (filter_by_price)

        验证：
        1. 价格相关请求可能触发价格筛选工具
        2. 工具正确处理价格范围
        """
        events = await self._collect_events("500元以下的耳机有哪些")

        tool_starts, tool_ends = self._extract_tool_events(events)

        # 检查是否调用了价格筛选工具
        price_tool_names = ["filter_by_price", "search_products"]
        tool_called = any(
            e["payload"].get("name") in price_tool_names for e in tool_starts
        )

        if tool_called:
            # 验证有对应的 tool.end
            for start in tool_starts:
                tool_name = start["payload"].get("name")
                if tool_name in price_tool_names:
                    # 查找对应的 end
                    matching_ends = [
                        e for e in tool_ends
                        if e["payload"].get("tool_call_id") == start["payload"].get("tool_call_id")
                    ]
                    assert len(matching_ends) >= 1, f"{tool_name} 缺少对应的 tool.end"

    async def test_get_product_details_tool(self):
        """测试商品详情工具 (get_product_details)

        验证：
        1. 详情请求可能触发商品详情工具
        2. 工具返回详细信息或错误
        """
        events = await self._collect_events("告诉我这款耳机的详细参数")

        tool_starts, tool_ends = self._extract_tool_events(events)

        # 可能触发详情工具
        detail_tool_called = any(
            e["payload"].get("name") == "get_product_details" for e in tool_starts
        )

        if detail_tool_called:
            detail_ends = [
                e for e in tool_ends
                if e["payload"].get("name") == "get_product_details"
            ]
            for end_event in detail_ends:
                payload = end_event["payload"]
                assert "status" in payload, "tool.end 缺少 status"

    async def test_compare_products_tool(self):
        """测试商品对比工具 (compare_products)

        验证：
        1. 对比请求可能触发对比工具
        2. 工具返回对比结果
        """
        events = await self._collect_events("对比一下索尼和Bose的降噪耳机")

        tool_starts, tool_ends = self._extract_tool_events(events)

        compare_tool_called = any(
            e["payload"].get("name") == "compare_products" for e in tool_starts
        )

        if compare_tool_called:
            compare_ends = [
                e for e in tool_ends
                if e["payload"].get("name") == "compare_products"
            ]
            assert len(compare_ends) >= 1, "compare_products 缺少 tool.end"

    async def test_tool_error_handling(self):
        """测试工具错误处理

        验证：
        1. 工具执行失败时返回 error 状态
        2. error 信息被正确记录
        """
        # 使用一个可能导致工具失败的查询（例如多品类查询）
        events = await self._collect_events("推荐耳机、手机、电脑")

        tool_starts, tool_ends = self._extract_tool_events(events)

        for end_event in tool_ends:
            payload = end_event["payload"]
            status = payload.get("status")

            if status == "error":
                # 错误时应有 error 信息
                assert "error" in payload or "message" in payload, "错误状态缺少错误信息"

    async def test_tool_call_duration(self):
        """测试工具调用耗时统计

        验证：
        1. 工具调用有合理的耗时
        2. tool.start 在 tool.end 之前
        """
        events = await self._collect_events("推荐一款耳机")

        tool_starts, tool_ends = self._extract_tool_events(events)

        if tool_starts and tool_ends:
            # 验证时序：start 在 end 之前
            for start in tool_starts:
                tool_call_id = start["payload"].get("tool_call_id")
                start_seq = start.get("seq", 0)

                matching_end = next(
                    (e for e in tool_ends if e["payload"].get("tool_call_id") == tool_call_id),
                    None,
                )

                if matching_end:
                    end_seq = matching_end.get("seq", 0)
                    assert end_seq > start_seq, "tool.end seq 应大于 tool.start seq"

    async def test_multiple_tool_calls(self):
        """测试多次工具调用

        验证：
        1. 复杂请求可能触发多次工具调用
        2. 每次调用都有完整的 start/end 对
        """
        events = await self._collect_events("先搜索降噪耳机，然后告诉我最便宜的那款的详细信息")

        tool_starts, tool_ends = self._extract_tool_events(events)

        if len(tool_starts) > 1:
            # 多次工具调用时，验证每个 start 都有对应的 end
            start_ids = {e["payload"]["tool_call_id"] for e in tool_starts}
            end_ids = {e["payload"]["tool_call_id"] for e in tool_ends}

            assert start_ids == end_ids, "工具调用 start/end 不匹配"

    async def test_tool_input_validation(self):
        """测试工具输入验证

        验证：
        1. 工具 input 参数被正确传递
        2. input 格式符合预期
        """
        events = await self._collect_events("搜索500元以下的蓝牙耳机")

        tool_starts, _ = self._extract_tool_events(events)

        for start in tool_starts:
            payload = start["payload"]
            tool_name = payload.get("name")

            # 验证基本结构
            assert "tool_call_id" in payload, f"{tool_name} 缺少 tool_call_id"

            # 如果有 input，验证是 dict
            if "input" in payload and payload["input"] is not None:
                assert isinstance(payload["input"], dict), f"{tool_name} input 应为 dict"

    async def test_tool_output_preview(self):
        """测试工具输出预览

        验证：
        1. tool.end 可能包含 output_preview
        2. output_preview 格式正确
        """
        events = await self._collect_events("推荐一款耳机")

        _, tool_ends = self._extract_tool_events(events)

        for end in tool_ends:
            payload = end["payload"]
            status = payload.get("status")

            if status == "success" and "output_preview" in payload:
                preview = payload["output_preview"]
                # output_preview 通常是列表（商品列表预览）
                if preview is not None:
                    assert isinstance(preview, (list, dict, str)), "output_preview 格式无效"
