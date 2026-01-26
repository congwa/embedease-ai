"""Crawler 提示词集成测试

验证爬虫提取提示词在真实 AI 调用场景下的效果。
"""

import json
import pytest

from tests.integration.prompts.conftest import (
    integration,
    invoke_llm,
    requires_api,
    slow,
)
from app.prompts.registry import get_default_prompt_content


@pytest.mark.anyio
@requires_api
@integration
@slow
class TestCrawlerPromptsIntegration:
    """Crawler 提示词集成测试"""

    async def test_product_extraction_returns_json(self, llm_model, sample_html_content):
        """测试商品信息提取提示词返回 JSON"""
        system_prompt = get_default_prompt_content("crawler.product_extraction")

        user_message = f"请分析以下 HTML 内容：\n\n{sample_html_content}"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        # 验证返回包含 JSON
        assert "{" in response and "}" in response

        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            result = json.loads(json_str)

            # 验证识别为商品页
            assert "is_product_page" in result
            assert result["is_product_page"] is True

            # 验证提取了商品信息
            if "product" in result:
                product = result["product"]
                # 验证包含关键字段
                assert any(
                    field in product
                    for field in ["title", "name", "price"]
                )
                # 验证提取了正确的品牌/产品名
                product_text = json.dumps(product, ensure_ascii=False)
                assert any(
                    keyword in product_text
                    for keyword in ["HHKB", "键盘", "2580", "静电容"]
                )

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_non_product_page_detection(self, llm_model):
        """测试非商品页面检测"""
        system_prompt = get_default_prompt_content("crawler.product_extraction")

        non_product_html = """
        <div class="blog-post">
            <h1>如何选择适合自己的机械键盘</h1>
            <p>本文将介绍机械键盘的选购要点...</p>
            <p>首先，我们需要了解不同轴体的特点...</p>
        </div>
        """

        user_message = f"请分析以下 HTML 内容：\n\n{non_product_html}"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        assert "{" in response and "}" in response

        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            result = json.loads(json_str)

            # 应该识别为非商品页
            assert "is_product_page" in result
            assert result["is_product_page"] is False

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_content_extraction_general(self, llm_model):
        """测试通用内容提取提示词"""
        system_prompt = get_default_prompt_content("crawler.content_extraction")

        article_html = """
        <article>
            <h1>2024年机械键盘选购指南</h1>
            <p class="author">作者：键盘爱好者</p>
            <p class="date">2024-01-15</p>
            <div class="content">
                <h2>轴体选择</h2>
                <p>机械键盘的核心是轴体，常见的有红轴、青轴、茶轴...</p>
                <h2>预算规划</h2>
                <p>入门级建议300-500元，进阶级500-1000元...</p>
            </div>
        </article>
        """

        user_message = f"请提取以下 HTML 的主要内容：\n\n{article_html}"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        assert "{" in response and "}" in response

        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            result = json.loads(json_str)

            # 验证提取了内容
            result_text = json.dumps(result, ensure_ascii=False)
            assert any(
                keyword in result_text
                for keyword in ["机械键盘", "选购", "轴体", "预算"]
            )

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")
