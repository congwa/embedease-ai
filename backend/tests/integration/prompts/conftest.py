"""提示词集成测试配置"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from typing import Any

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


# 标记：需要真实 API
requires_api = pytest.mark.skipif(
    not _has_api_config(),
    reason="需要配置真实的 LLM_API_KEY 和 LLM_PROVIDER",
)

# 标记：集成测试
integration = pytest.mark.integration

# 标记：慢速测试
slow = pytest.mark.slow


@pytest.fixture
def llm_model():
    """获取真实 LLM 模型"""
    from app.core.llm import get_chat_model

    return get_chat_model()


@pytest.fixture
def sample_conversation() -> list[dict[str, str]]:
    """示例对话数据"""
    return [
        {"role": "user", "content": "你好，我想买一款适合程序员用的机械键盘，预算500左右"},
        {"role": "assistant", "content": "好的，我来帮您推荐。您平时主要用来写代码还是打游戏呢？"},
        {"role": "user", "content": "主要写代码，长时间打字，希望手感舒适"},
    ]


@pytest.fixture
def sample_html_content() -> str:
    """示例商品页面 HTML"""
    return """
    <div class="product-detail">
        <h1 class="title">HHKB Professional HYBRID Type-S 静电容键盘</h1>
        <div class="price">¥2,580.00</div>
        <div class="description">
            经典的 60% 布局，静电容轴体，静音设计，蓝牙/USB双模连接，
            专为程序员设计的高端键盘。
        </div>
        <ul class="specs">
            <li>轴体：静电容</li>
            <li>布局：60%</li>
            <li>连接：蓝牙/USB</li>
        </ul>
    </div>
    """


@pytest.fixture
def sample_skill_description() -> str:
    """示例技能描述"""
    return "当用户询问商品价格区间时，帮助筛选对应价位的商品，并按性价比排序推荐"


async def invoke_llm(model: Any, system_prompt: str, user_message: str) -> str:
    """调用 LLM 的辅助函数"""
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    response = await model.ainvoke(messages)
    return response.content
