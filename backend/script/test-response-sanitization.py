"""测试响应清洗中间件的实际效果

演示如何检测和处理异常的 function calling 响应
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware


async def test_malformed_responses():
    """测试各种异常响应格式"""
    
    print("🧪 测试响应清洗中间件")
    print("=" * 60)
    
    # 创建中间件
    middleware = ResponseSanitizationMiddleware(enabled=True)
    
    # 测试用例：各种异常格式
    test_cases = [
        {
            "name": "Function Call with ID",
            "content": '[function:search_products:2{"query": "降噪耳机"}]',
            "should_sanitize": True,
        },
        {
            "name": "Function Call without ID",
            "content": '[function:search_products{"query": "test"}]',
            "should_sanitize": True,
        },
        {
            "name": "Tool Call",
            "content": "[tool:search_products]",
            "should_sanitize": True,
        },
        {
            "name": "XML Function",
            "content": "<function>search_products</function>",
            "should_sanitize": True,
        },
        {
            "name": "JSON Function",
            "content": '{"function": {"name": "search_products"}}',
            "should_sanitize": True,
        },
        {
            "name": "JSON Array Tool Call (New Format)",
            "content": '[{"name": "search_products", "parameters": {"query": "降噪耳机"}, "id": "search_products:0"}]',
            "should_sanitize": True,
        },
        {
            "name": "Normal Response",
            "content": "根据您的需求，我为您推荐以下商品：",
            "should_sanitize": False,
        },
        {
            "name": "Normal Structured Output",
            "content": '{"products": [{"name": "test", "price": 100}]}',
            "should_sanitize": False,
        },
    ]
    
    # 模拟请求和处理器
    mock_request = MagicMock(spec=ModelRequest)
    mock_request.model = MagicMock()
    mock_request.model.model_name = "test-model"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试 {i}: {test_case['name']}")
        print(f"原始内容: {test_case['content'][:80]}{'...' if len(test_case['content']) > 80 else ''}")
        
        # 创建模拟响应
        mock_handler = AsyncMock()
        mock_response = MagicMock(spec=ModelResponse)
        mock_response.result = [AIMessage(content=test_case['content'])]
        mock_handler.return_value = mock_response
        
        # 调用中间件
        result = await middleware.awrap_model_call(mock_request, mock_handler)
        
        # 检查结果
        result_content = result.result[0].content
        was_sanitized = result_content != test_case['content']
        
        if was_sanitized:
            print(f"✅ 已清洗")
            print(f"清洗后: {result_content[:80]}...")
        else:
            print(f"✓ 保持原样")
        
        # 验证预期
        if was_sanitized == test_case['should_sanitize']:
            print(f"🎯 符合预期")
        else:
            print(f"❌ 不符合预期！")
    
    print("\n" + "=" * 60)
    print("📊 统计信息")
    stats = ResponseSanitizationMiddleware.get_statistics()
    print(f"总响应数: {stats['total_responses']}")
    print(f"异常数量: {stats['malformed_count']}")
    print(f"异常率: {stats['malformed_rate']:.2f}%")


async def test_custom_message():
    """测试自定义降级消息"""
    
    print("\n" + "=" * 60)
    print("🎨 测试自定义降级消息")
    print("=" * 60)
    
    custom_msg = "系统维护中，请稍后再试。🔧"
    middleware = ResponseSanitizationMiddleware(
        enabled=True,
        custom_fallback_message=custom_msg,
    )
    
    # 创建异常响应
    mock_request = MagicMock(spec=ModelRequest)
    mock_request.model = MagicMock()
    mock_request.model.model_name = "test-model"
    
    mock_handler = AsyncMock()
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.result = [AIMessage(content='[function:test:1{"x": "y"}]')]
    mock_handler.return_value = mock_response
    
    result = await middleware.awrap_model_call(mock_request, mock_handler)
    
    print(f"原始内容: [function:test:1{{\"x\": \"y\"}}]")
    print(f"自定义消息: {result.result[0].content}")
    
    if result.result[0].content == custom_msg:
        print("✅ 自定义消息生效")
    else:
        print("❌ 自定义消息未生效")


async def test_disabled_middleware():
    """测试禁用中间件"""
    
    print("\n" + "=" * 60)
    print("🔌 测试禁用中间件")
    print("=" * 60)
    
    middleware = ResponseSanitizationMiddleware(enabled=False)
    
    # 创建异常响应
    mock_request = MagicMock(spec=ModelRequest)
    mock_request.model = MagicMock()
    mock_request.model.model_name = "test-model"
    
    mock_handler = AsyncMock()
    malformed_content = '[function:test:1{"x": "y"}]'
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.result = [AIMessage(content=malformed_content)]
    mock_handler.return_value = mock_response
    
    result = await middleware.awrap_model_call(mock_request, mock_handler)
    
    print(f"原始内容: {malformed_content}")
    print(f"处理后: {result.result[0].content}")
    
    if result.result[0].content == malformed_content:
        print("✅ 禁用生效，内容未被修改")
    else:
        print("❌ 禁用未生效")


async def main():
    """主函数"""
    print("\n🚀 响应清洗中间件测试")
    print("=" * 60)
    
    # 重置统计
    ResponseSanitizationMiddleware.reset_statistics()
    
    # 运行测试
    await test_malformed_responses()
    await test_custom_message()
    await test_disabled_middleware()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("\n💡 使用建议:")
    print("  • 生产环境建议启用此中间件")
    print("  • 定期检查异常率统计")
    print("  • 如果异常率过高，考虑更换模型")
    print("  • 可以自定义降级消息以符合业务场景")


if __name__ == "__main__":
    asyncio.run(main())

