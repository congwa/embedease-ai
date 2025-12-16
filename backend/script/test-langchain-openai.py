"""
LangChain + SiliconFlow 硅基流动集成示例
使用 SiliconFlow 的 API 构建智能代理
"""

from langchain_openai import ChatOpenAI

# from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain.tools import tool


@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    # 模拟天气API调用 - 实际应用中可以调用真实的天气API
    weather_data = {
        "北京": "晴天，温度25°C，湿度45%",
        "上海": "多云，温度22°C，湿度60%",
        "深圳": "雨天，温度28°C，湿度80%",
        "广州": "阴天，温度26°C，湿度70%",
        "杭州": "小雨，温度20°C，湿度75%",
        "sf": "Sunny in San Francisco, 72°F",  # 兼容英文查询
        "san francisco": "Sunny in San Francisco, 72°F",
    }
    return weather_data.get(city.lower(), f"{city}的天气信息：晴天，温度20-25°C")


@tool
def calculate_math(expression: str) -> str:
    """计算数学表达式"""
    try:
        # 注意：实际应用中应该使用更安全的计算方式
        result = eval(expression)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算错误：{str(e)}"


@tool
def search_info(query: str) -> str:
    """搜索相关信息"""
    # 模拟搜索功能 - 实际应用中可以调用搜索引擎API
    search_results = {
        "人工智能": "人工智能（AI）是计算机科学的一个分支，致力于创建能够模拟人类智能的机器。",
        "机器学习": "机器学习是AI的一个子集，通过算法让计算机从数据中学习并做出预测。",
        "深度学习": "深度学习使用神经网络模拟人脑处理信息的方式。",
        "硅基流动": "硅基流动是一家提供AI模型API服务的云平台。",
    }

    for key, value in search_results.items():
        if key in query:
            return f"搜索结果：{value}"

    return f"为查询 '{query}' 找到的相关信息，请使用更具体的关键词。"


def main():
    """主函数：演示 LangChain + SiliconFlow 的智能代理"""

    print("🚀 LangChain + SiliconFlow 硅基流动集成示例")
    print("=" * 60)

    # 初始化 SiliconFlow ChatOpenAI 模型
    siliconflow_model = ChatOpenAI(
        model="moonshotai/Kimi-K2-Thinking",  # 使用 SiliconFlow 支持的模型
        openai_api_key="sk-jxkuiiukbesibqapqognjxgxodhjnjzjzcfpkmgnowsdlrqx",  # SiliconFlow API Key
        openai_api_base="https://api.siliconflow.cn/v1",  # SiliconFlow 基础URL
        temperature=0.7,
        max_tokens=1500,
        verbose=True,
    )

    print("🤖 初始化 SiliconFlow 模型完成")
    print(f"📋 使用的模型: moonshotai/Kimi-K2-Thinking")
    print(f"🌐 API 端点: https://api.siliconflow.cn/v1")
    print()

    # 首先测试模型的流式功能（学习 2.py）
    print("🧪 先测试模型的流式功能...")
    test_question = "简单介绍一下人工智能"
    print(f"❓ 测试问题: {test_question}")

    try:
        print(f"🤖 AI 回复：", end="", flush=True)

        full_response = ""
        reasoning_content = ""

        # 直接使用模型的流式调用（学习 2.py 的方式）
        stream_response = siliconflow_model.stream([{"role": "user", "content": test_question}])

        # 处理流式响应，参考 2.py 的实现
        for chunk in stream_response:
            print(f"chunk: {chunk}")  # 调试输出

            # LangChain AIMessageChunk 处理
            if hasattr(chunk, "content") and chunk.content:
                content_part = chunk.content
                print(content_part, end="", flush=True)
                full_response += content_part

            # 处理推理内容（如果有）
            if (
                hasattr(chunk, "additional_kwargs")
                and "reasoning_content" in chunk.additional_kwargs
            ):
                reasoning_part = chunk.additional_kwargs["reasoning_content"]
                print(f"\n🧠 推理过程: {reasoning_part}", end="", flush=True)
                reasoning_content += reasoning_part

        print(f"\n\n✅ 模型流式测试完成！")
        print(f"📊 响应总长度: {len(full_response)} 字符")
        if reasoning_content:
            print(f"🧠 推理内容长度: {len(reasoning_content)} 字符")

    except Exception as e:
        print(f"\n❌ 模型流式测试失败: {str(e)}")
        return

    print("\n" + "=" * 60)

    # 创建智能代理
    agent = create_agent(
        model=siliconflow_model,
        tools=[get_weather, calculate_math, search_info],
        system_prompt="""你是一个智能助手，使用 SiliconFlow 的 AI 模型提供服务。
你可以调用以下工具来帮助用户：
- get_weather: 获取天气信息
- calculate_math: 计算数学表达式
- search_info: 搜索相关信息

请用中文回答用户的问题，并根据需要调用合适的工具。""",
    )

    print("🛠️ 创建智能代理完成")
    print("📋 可用工具: get_weather, calculate_math, search_info")
    print()

    # 测试问题列表
    test_questions = [
        "北京今天的天气怎么样？",
        "计算 15 + 27 等于多少？",
        "什么是人工智能？",
        "请帮我查询杭州的天气",
        "计算 (2 + 3) * 4 的结果",
    ]

    print("🧪 开始测试智能代理功能...")
    print()

    for i, question in enumerate(test_questions, 1):
        print(f"❓ 测试 {i}: {question}")

        try:
            # 使用流式调用，学习 2.py 的 chunk 处理方式
            print(f"🤖 AI 回复：", end="", flush=True)

            full_response = ""
            reasoning_content = ""

            # 直接使用模型的流式调用（学习 2.py 的方式）
            stream_response = siliconflow_model.stream([{"role": "user", "content": question}])

            # 处理流式响应，参考 2.py 的实现
            for chunk in stream_response:
                print(f"chunk: {chunk}")  # 调试输出

                # LangChain AIMessageChunk 处理
                if hasattr(chunk, "content") and chunk.content:
                    content_part = chunk.content
                    print(content_part, end="", flush=True)
                    full_response += content_part

                # 处理推理内容（如果有）
                if (
                    hasattr(chunk, "additional_kwargs")
                    and "reasoning_content" in chunk.additional_kwargs
                ):
                    reasoning_part = chunk.additional_kwargs["reasoning_content"]
                    print(f"\n🧠 推理过程: {reasoning_part}", end="", flush=True)
                    reasoning_content += reasoning_part

            print(f"\n\n✅ 调用完成！")
            print(f"📊 响应总长度: {len(full_response)} 字符")
            if reasoning_content:
                print(f"🧠 推理内容长度: {len(reasoning_content)} 字符")
            print("✅ 成功")

        except Exception as e:
            print(f"❌ 错误: {str(e)}")
            print("⚠️ 可能的原因: API 密钥无效、网络连接问题或模型不可用")

        print("-" * 50)
        print()

    print("🎉 所有测试完成！")
    print("\n💡 使用 SiliconFlow 的优势:")
    print("  • 稳定的 API 服务")
    print("  • 支持多种主流模型")
    print("  • 灵活的计费方式")
    print("  • 良好的中文支持")
    print("\n🔗 了解更多: https://siliconflow.cn/")


if __name__ == "__main__":
    main()
