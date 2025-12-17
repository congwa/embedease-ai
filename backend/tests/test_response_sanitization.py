"""测试响应清洗中间件"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware


@pytest.fixture
def middleware():
    """创建中间件实例"""
    return ResponseSanitizationMiddleware(enabled=True)


@pytest.fixture
def mock_request():
    """创建模拟请求"""
    request = MagicMock(spec=ModelRequest)
    request.model = MagicMock()
    request.model.model_name = "test-model"
    return request


@pytest.fixture
def mock_handler():
    """创建模拟处理器"""
    return AsyncMock()


class TestMalformedDetection:
    """测试异常格式检测"""

    def test_detect_function_call_with_id(self):
        """测试检测 [function:tool_name:1{...}] 格式"""
        content = '[function:search_products:2{"query": "降噪耳机"}]'
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_detect_function_call_without_id(self):
        """测试检测 [function:tool_name{...}] 格式"""
        content = '[function:search_products{"query": "test"}]'
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_detect_tool_call(self):
        """测试检测 [tool:xxx] 格式"""
        content = "[tool:search_products]"
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_detect_xml_function(self):
        """测试检测 <function>...</function> 格式"""
        content = "<function>search_products</function>"
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_detect_json_function(self):
        """测试检测 JSON function 格式"""
        content = '{"function": {"name": "search_products"}}'
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_detect_json_array_tool_call(self):
        """测试检测 JSON 数组格式的工具调用"""
        content = '[{"name": "search_products", "parameters": {"query": "降噪耳机"}, "id": "search_products:0"}]'
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True
        
    def test_detect_json_array_multiple_tools(self):
        """测试检测包含多个工具的 JSON 数组"""
        content = '[{"name": "tool1", "parameters": {}, "id": "1"}, {"name": "tool2", "parameters": {}, "id": "2"}]'
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_detect_uuid_tool_call_format(self):
        """测试检测 UUID 格式的工具调用"""
        content = '[5d177dc5-a153-4f8a-9b89-b38b9e5231a0]:0{"query": "降噪耳机"}<|tool_calls_section_end|>'
        assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True
        
    def test_detect_tool_calls_markers(self):
        """测试检测包含工具调用特殊标记的内容"""
        test_cases = [
            '<|tool_calls_section_end|>',
            'some text <|tool_sep|> more text',
            '<|tool_start|>function_name',
        ]
        for content in test_cases:
            assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is True

    def test_normal_content_not_detected(self):
        """测试正常内容不会被检测为异常"""
        normal_contents = [
            "这是一个正常的回复",
            "根据您的需求，我推荐以下商品：",
            "抱歉，我没有找到相关商品。",
            '{"products": [{"name": "test"}]}',  # 正常的结构化输出
            '[{"title": "商品1", "description": "描述", "price": 100}]',  # 正常的商品列表
            '[{"id": "1", "title": "Product", "description": "Desc"}]',  # 包含id但是商品数据
        ]
        for content in normal_contents:
            assert ResponseSanitizationMiddleware._is_malformed_function_call(content) is False

    def test_empty_content(self):
        """测试空内容"""
        assert ResponseSanitizationMiddleware._is_malformed_function_call("") is False
        assert ResponseSanitizationMiddleware._is_malformed_function_call("   ") is False


class TestMiddlewareProcessing:
    """测试中间件处理逻辑"""

    @pytest.mark.asyncio
    async def test_disabled_middleware_passthrough(self, mock_request, mock_handler):
        """测试禁用时直接透传"""
        middleware = ResponseSanitizationMiddleware(enabled=False)
        
        mock_response = MagicMock(spec=ModelResponse)
        mock_handler.return_value = mock_response

        result = await middleware.awrap_model_call(mock_request, mock_handler)
        
        assert result == mock_response
        mock_handler.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_sanitize_malformed_response(self, middleware, mock_request, mock_handler):
        """测试清洗异常响应"""
        # 创建包含异常内容的响应
        malformed_message = AIMessage(
            content='[function:search_products:2{"query": "降噪耳机"}]'
        )
        mock_response = MagicMock(spec=ModelResponse)
        mock_response.result = [malformed_message]
        mock_handler.return_value = mock_response

        result = await middleware.awrap_model_call(mock_request, mock_handler)

        # 验证内容已被替换
        assert len(result.result) == 1
        sanitized_msg = result.result[0]
        assert isinstance(sanitized_msg, AIMessage)
        assert "抱歉" in sanitized_msg.content
        assert "技术问题" in sanitized_msg.content
        assert "function" not in sanitized_msg.content

    @pytest.mark.asyncio
    async def test_normal_response_unchanged(self, middleware, mock_request, mock_handler):
        """测试正常响应不被修改"""
        normal_message = AIMessage(content="这是一个正常的回复，推荐以下商品：")
        mock_response = MagicMock(spec=ModelResponse)
        mock_response.result = [normal_message]
        mock_handler.return_value = mock_response

        result = await middleware.awrap_model_call(mock_request, mock_handler)

        # 验证内容未被修改
        assert len(result.result) == 1
        assert result.result[0].content == "这是一个正常的回复，推荐以下商品："

    @pytest.mark.asyncio
    async def test_custom_fallback_message(self, mock_request, mock_handler):
        """测试自定义降级消息"""
        custom_msg = "系统维护中，请稍后再试。"
        middleware = ResponseSanitizationMiddleware(
            enabled=True,
            custom_fallback_message=custom_msg,
        )

        malformed_message = AIMessage(content='[function:test:1{"x": "y"}]')
        mock_response = MagicMock(spec=ModelResponse)
        mock_response.result = [malformed_message]
        mock_handler.return_value = mock_response

        result = await middleware.awrap_model_call(mock_request, mock_handler)

        assert result.result[0].content == custom_msg

    @pytest.mark.asyncio
    async def test_list_content_handling(self, middleware, mock_request, mock_handler):
        """测试处理列表类型的内容"""
        # 某些模型可能返回列表格式的内容
        malformed_message = AIMessage(
            content=['[function:test:1{"x": "y"}]']
        )
        mock_response = MagicMock(spec=ModelResponse)
        mock_response.result = [malformed_message]
        mock_handler.return_value = mock_response

        result = await middleware.awrap_model_call(mock_request, mock_handler)

        # 验证已被清洗
        assert "抱歉" in result.result[0].content


class TestStatistics:
    """测试统计功能"""

    def test_statistics_tracking(self):
        """测试统计计数"""
        # 重置统计
        ResponseSanitizationMiddleware.reset_statistics()
        
        stats = ResponseSanitizationMiddleware.get_statistics()
        assert stats["total_responses"] == 0
        assert stats["malformed_count"] == 0
        assert stats["malformed_rate"] == 0.0

    def test_reset_statistics(self):
        """测试重置统计"""
        # 手动设置一些值
        ResponseSanitizationMiddleware._total_responses = 100
        ResponseSanitizationMiddleware._malformed_count = 10
        
        # 重置
        ResponseSanitizationMiddleware.reset_statistics()
        
        stats = ResponseSanitizationMiddleware.get_statistics()
        assert stats["total_responses"] == 0
        assert stats["malformed_count"] == 0


class TestFallbackMessage:
    """测试降级消息生成"""

    def test_default_fallback_message(self):
        """测试默认降级消息"""
        middleware = ResponseSanitizationMiddleware()
        msg = middleware._get_fallback_message("original content")
        
        assert "抱歉" in msg
        assert "技术问题" in msg
        assert "重试" in msg

    def test_custom_fallback_message(self):
        """测试自定义降级消息"""
        custom_msg = "自定义错误消息"
        middleware = ResponseSanitizationMiddleware(custom_fallback_message=custom_msg)
        msg = middleware._get_fallback_message("original content")
        
        assert msg == custom_msg

