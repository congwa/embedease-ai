"""StreamingResponseHandler 测试

测试流响应处理器的商品数据收集和延迟推送逻辑。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from langgraph_agent_kit import StreamingResponseHandler
from app.services.agent.streams.business_handler import (
    BusinessResponseHandler,
    normalize_products_payload,
)


def run_async(coro):
    """运行异步函数的辅助函数"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestNormalizeProductsPayload:
    """测试商品数据标准化函数"""

    def test_normalize_list_input(self):
        """测试列表输入"""
        payload = [
            {"id": "P001", "name": "商品1"},
            {"id": "P002", "name": "商品2"},
        ]
        result = normalize_products_payload(payload)
        assert result is not None
        assert len(result) == 2
        assert result[0]["id"] == "P001"

    def test_normalize_dict_with_products_key(self):
        """测试带 products 键的字典输入"""
        payload = {
            "products": [
                {"id": "P001", "name": "商品1"},
            ]
        }
        result = normalize_products_payload(payload)
        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "P001"

    def test_normalize_converts_id_to_string(self):
        """测试 ID 转换为字符串"""
        payload = [{"id": 123, "name": "商品"}]
        result = normalize_products_payload(payload)
        assert result is not None
        assert result[0]["id"] == "123"

    def test_normalize_filters_items_without_id(self):
        """测试过滤无 ID 的项"""
        payload = [
            {"id": "P001", "name": "有ID"},
            {"name": "无ID"},
        ]
        result = normalize_products_payload(payload)
        assert result is not None
        assert len(result) == 1

    def test_normalize_none_input(self):
        """测试 None 输入"""
        result = normalize_products_payload(None)
        assert result is None

    def test_normalize_empty_list(self):
        """测试空列表"""
        result = normalize_products_payload([])
        assert result is None

    def test_normalize_invalid_type(self):
        """测试无效类型"""
        result = normalize_products_payload("invalid")
        assert result is None


class TestStreamingResponseHandlerInit:
    """测试 StreamingResponseHandler 初始化"""

    def test_init_with_emitter(self):
        """测试使用 emitter 初始化"""
        emitter = MagicMock()
        handler = StreamingResponseHandler(emitter=emitter)
        assert handler.emitter is emitter
        assert handler.full_content == ""
        assert handler.full_reasoning == ""
        # SDK 版本没有 products_data，使用 BusinessResponseHandler 测试

    def test_init_with_conversation_id(self):
        """测试带会话 ID 初始化"""
        emitter = MagicMock()
        handler = StreamingResponseHandler(
            emitter=emitter,
            conversation_id="conv-123",
        )
        assert handler.conversation_id == "conv-123"


class TestStreamingResponseHandlerProducts:
    """测试商品数据收集和推送逻辑（使用 BusinessResponseHandler）"""

    @pytest.fixture
    def handler(self):
        """创建测试用的 handler"""
        emitter = MagicMock()
        emitter.aemit = AsyncMock()
        return BusinessResponseHandler(
            emitter=emitter,
            conversation_id="test-conv",
        )

    def test_products_data_initially_none(self, handler):
        """测试商品数据初始为 None"""
        assert handler.products_data is None

    def test_products_data_can_be_set(self, handler):
        """测试商品数据可以设置"""
        handler.products_data = [{"id": "P001", "name": "商品"}]
        assert handler.products_data is not None
        assert len(handler.products_data) == 1

    def test_finalize_emits_products_when_present(self, handler):
        """测试 finalize 时推送商品数据"""
        handler.products_data = [{"id": "P001", "name": "商品"}]
        handler.full_content = "测试回复"
        
        run_async(handler.finalize())
        
        # 检查是否发射了商品事件
        calls = handler.emitter.aemit.call_args_list
        event_types = [call[0][0] for call in calls]
        assert "assistant.products" in event_types

    def test_finalize_skips_products_when_none(self, handler):
        """测试没有商品时不推送"""
        handler.products_data = None
        handler.full_content = "测试回复"
        
        run_async(handler.finalize())
        
        # 检查没有发射商品事件
        calls = handler.emitter.aemit.call_args_list
        event_types = [call[0][0] for call in calls]
        assert "assistant.products" not in event_types

    def test_finalize_emits_final_event(self, handler):
        """测试 finalize 发射最终事件"""
        handler.full_content = "测试回复"
        
        result = run_async(handler.finalize())
        
        # 检查发射了 final 事件
        calls = handler.emitter.aemit.call_args_list
        event_types = [call[0][0] for call in calls]
        assert "assistant.final" in event_types
        
        # 检查返回结果
        assert result["content"] == "测试回复"


class TestProductsMerging:
    """测试商品去重合并逻辑"""

    def test_merge_products_dedup_by_id(self):
        """测试按 ID 去重"""
        products1 = [{"id": "P001", "name": "商品1"}]
        products2 = [{"id": "P001", "name": "商品1重复"}, {"id": "P002", "name": "商品2"}]
        
        # 模拟合并逻辑
        merged = products1.copy()
        seen_ids = {p.get("id") for p in merged}
        for product in products2:
            if product.get("id") not in seen_ids:
                merged.append(product)
                seen_ids.add(product.get("id"))
        
        assert len(merged) == 2
        assert merged[0]["id"] == "P001"
        assert merged[1]["id"] == "P002"

    def test_merge_preserves_order(self):
        """测试合并保持顺序"""
        products1 = [{"id": "P001", "name": "商品1"}]
        products2 = [{"id": "P002", "name": "商品2"}, {"id": "P003", "name": "商品3"}]
        
        merged = products1.copy()
        seen_ids = {p.get("id") for p in merged}
        for product in products2:
            if product.get("id") not in seen_ids:
                merged.append(product)
                seen_ids.add(product.get("id"))
        
        assert [p["id"] for p in merged] == ["P001", "P002", "P003"]
