"""
SiliconFlow 硅基流动 OpenAI API 直接调用示例
演示如何使用 SiliconFlow 的 API 进行 AI 模型推理
"""

from openai import OpenAI


def main():
    """
    主函数：演示 SiliconFlow API 的基本使用
    """
    print("🚀 SiliconFlow 硅基流动 OpenAI API 调用示例")
    print("=" * 60)

    try:
        # 初始化 SiliconFlow OpenAI 客户端
        print("🔧 初始化 SiliconFlow 客户端...")
        client = OpenAI(
            api_key="sk-jxkuiiukbesibqapqognjxgxodhjnjzjzcfpkmgnowsdlrqx",  # SiliconFlow API Key
            base_url="https://api.siliconflow.cn/v1",  # SiliconFlow 基础URL
        )
        print("✅ 客户端初始化完成")

        print("\n🤖 正在调用 SiliconFlow API...")
        print("📋 使用的模型: moonshotai/Kimi-K2-Thinking")
        print("🌐 API 端点: https://api.siliconflow.cn/v1")

        # 调用 chat completions 接口
        response = client.chat.completions.create(
            model="moonshotai/Kimi-K2-Thinking",  # SiliconFlow 支持的推理模型
            messages=[
                {"role": "user", "content": "推理模型会给市场带来哪些新的机会？请详细分析。"}
            ],
            stream=True,  # 启用流式输出
            max_tokens=2000,  # 设置最大token数
            temperature=0.7,  # 设置温度参数（控制创造性）
            top_p=0.9,  # 设置top-p参数
        )

        print("\n💬 AI 回复：", end="", flush=True)

        # 处理流式响应
        full_response = ""
        reasoning_content = ""

        for chunk in response:
            if not chunk.choices:
                continue
            print(f"chunk: {chunk}")
            # 输出推理内容（如果有）
            if (
                hasattr(chunk.choices[0].delta, "reasoning_content")
                and chunk.choices[0].delta.reasoning_content
            ):
                reasoning_part = chunk.choices[0].delta.reasoning_content
                print(f"\n🧠 推理过程: {reasoning_part}", end="", flush=True)
                reasoning_content += reasoning_part

            # 输出内容
            elif chunk.choices[0].delta.content:
                content_part = chunk.choices[0].delta.content
                print(content_part, end="", flush=True)
                full_response += content_part

        print("\n\n✅ 调用完成！")
        print(f"📊 响应总长度: {len(full_response)} 字符")
        if reasoning_content:
            print(f"🧠 推理内容长度: {len(reasoning_content)} 字符")

        print("\n💡 SiliconFlow 特色功能:")
        print("  • 支持多种主流推理模型")
        print("  • 实时流式输出")
        print("  • 推理过程可视化")
        print("  • 灵活的计费方式")
        print("  • 稳定的API服务")

    except Exception as e:
        print(f"\n❌ 调用失败：{str(e)}")
        print("\n🔧 故障排除:")
        print("1. 检查 API Key 是否正确")
        print("2. 确认网络连接是否正常")
        print("3. 验证 SiliconFlow 服务是否可用")
        print("4. 检查模型名称是否正确")
        print("5. 确认账户余额充足")
        print("\n🔗 SiliconFlow 官网: https://siliconflow.cn/")


if __name__ == "__main__":
    main()
