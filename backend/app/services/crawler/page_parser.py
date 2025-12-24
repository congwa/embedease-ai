"""页面解析器

支持两种解析模式：
1. selector: CSS/XPath 选择器模式，适用于结构规律的网站
2. llm: LLM 智能解析模式，适用于复杂或不规律的网站（默认）
"""

import json
import re
from typing import Any

from bs4 import BeautifulSoup
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.crawler import ExtractionConfig, ExtractionMode, ParsedProductData

logger = get_logger("crawler.parser")


class ProductExtractionOutput(BaseModel):
    """LLM 商品提取输出格式"""

    is_product_page: bool = Field(description="是否为商品详情页")
    product: ParsedProductData | None = Field(
        None, description="提取的商品数据（如果是商品页）"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="提取置信度"
    )
    reason: str | None = Field(None, description="判断理由")


DEFAULT_EXTRACTION_PROMPT = """你是一个专业的网页商品信息提取助手。请分析以下 HTML 内容，判断是否为商品详情页，如果是则提取商品信息。

## 判断标准
商品详情页通常包含：
- 商品名称/标题
- 价格信息
- 商品描述或详情
- 购买/加入购物车按钮

## 提取字段
如果是商品页，请提取以下信息（尽可能完整）：
- name: 商品名称（必填）
- price: 价格（数字，不含货币符号）
- summary: 核心卖点/简介
- description: 详细描述
- category: 商品分类
- tags: 标签列表
- brand: 品牌
- image_urls: 图片链接列表
- specs: 规格参数（如颜色、尺寸等）

## 输出格式
请以 JSON 格式输出，包含以下字段：
{{
  "is_product_page": true/false,
  "product": {{ ... }} 或 null,
  "confidence": 0.0-1.0,
  "reason": "判断理由"
}}

## HTML 内容
{html_content}
"""


class PageParser:
    """页面解析器"""

    def __init__(self, llm=None):
        """初始化解析器

        Args:
            llm: LangChain LLM 实例，如果为 None 则延迟初始化
        """
        self._llm = llm
        self._parser = JsonOutputParser(pydantic_object=ProductExtractionOutput)

    @property
    def llm(self):
        """延迟初始化 LLM"""
        if self._llm is None:
            from app.core.llm import get_chat_model

            # 使用爬取专用模型或默认模型
            self._llm = get_chat_model(
                model=settings.CRAWLER_MODEL or settings.LLM_CHAT_MODEL,
                provider=settings.CRAWLER_PROVIDER or settings.LLM_PROVIDER,
                api_key=settings.effective_crawler_api_key,
                base_url=settings.effective_crawler_base_url,
            )
        return self._llm

    def parse_with_selector(
        self, html: str, config: ExtractionConfig
    ) -> tuple[bool, ParsedProductData | None, str | None]:
        """使用 CSS 选择器解析页面

        Args:
            html: HTML 内容
            config: 提取配置

        Returns:
            (is_product_page, parsed_data, error)
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            fields = config.fields

            if not fields:
                return False, None, "未配置字段选择器"

            # 检查是否为商品页
            if config.product_page_indicator:
                indicator = soup.select_one(config.product_page_indicator)
                if not indicator:
                    return False, None, None

            # 提取字段
            data: dict[str, Any] = {}

            # 提取文本字段
            text_fields = ["name", "summary", "description", "category", "brand"]
            for field in text_fields:
                selector = getattr(fields, field, None)
                if selector:
                    elem = soup.select_one(selector.replace("::text", ""))
                    if elem:
                        data[field] = elem.get_text(strip=True)

            # 提取价格
            if fields.price:
                price_elem = soup.select_one(fields.price.replace("::text", ""))
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    # 提取数字
                    price_match = re.search(r"[\d,]+\.?\d*", price_text)
                    if price_match:
                        data["price"] = float(price_match.group().replace(",", ""))

            # 提取标签
            if fields.tags:
                tag_elems = soup.select(fields.tags.replace("::text", ""))
                if tag_elems:
                    data["tags"] = [t.get_text(strip=True) for t in tag_elems]

            # 提取图片
            if fields.image_urls:
                img_elems = soup.select(fields.image_urls)
                if img_elems:
                    data["image_urls"] = [
                        img.get("src") or img.get("data-src")
                        for img in img_elems
                        if img.get("src") or img.get("data-src")
                    ]

            # 提取规格
            if fields.specs:
                spec_elems = soup.select(fields.specs)
                if spec_elems:
                    specs = {}
                    for elem in spec_elems:
                        text = elem.get_text(strip=True)
                        if ":" in text or "：" in text:
                            parts = re.split(r"[:：]", text, 1)
                            if len(parts) == 2:
                                specs[parts[0].strip()] = parts[1].strip()
                    if specs:
                        data["specs"] = specs

            # 检查是否有必要字段
            if not data.get("name"):
                return False, None, None

            return True, ParsedProductData(**data), None

        except Exception as e:
            logger.error("选择器解析失败", error=str(e))
            return False, None, str(e)

    async def parse_with_llm(
        self, html: str, url: str, prompt: str | None = None
    ) -> tuple[bool, ParsedProductData | None, str | None]:
        """使用 LLM 解析页面

        Args:
            html: HTML 内容
            url: 页面 URL
            prompt: 自定义提示词

        Returns:
            (is_product_page, parsed_data, error)
        """
        try:
            # 清理 HTML，只保留主要内容
            cleaned_html = self._clean_html(html)

            # 截断过长的内容
            max_length = settings.CRAWLER_MAX_HTML_LENGTH
            if len(cleaned_html) > max_length:
                cleaned_html = cleaned_html[:max_length] + "\n... [内容已截断]"

            # 构建提示词
            extraction_prompt = prompt or DEFAULT_EXTRACTION_PROMPT
            formatted_prompt = extraction_prompt.format(html_content=cleaned_html)

            # 调用 LLM
            messages = [
                SystemMessage(
                    content="你是一个专业的网页信息提取助手。请严格按照 JSON 格式输出。"
                ),
                HumanMessage(content=formatted_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            content = response.content

            # 解析 JSON
            # 尝试从响应中提取 JSON
            json_match = re.search(r"\{[\s\S]*\}", content)
            if not json_match:
                return False, None, "LLM 响应中未找到有效 JSON"

            result = json.loads(json_match.group())

            is_product_page = result.get("is_product_page", False)
            if not is_product_page:
                return False, None, None

            product_data = result.get("product")
            if not product_data:
                return False, None, None

            # 补充 URL
            if not product_data.get("url"):
                product_data["url"] = url

            return True, ParsedProductData(**product_data), None

        except json.JSONDecodeError as e:
            logger.error("LLM 响应 JSON 解析失败", error=str(e))
            return False, None, f"JSON 解析失败: {e}"
        except Exception as e:
            logger.error("LLM 解析失败", error=str(e))
            return False, None, str(e)

    async def parse(
        self, html: str, url: str, config: ExtractionConfig | None = None
    ) -> tuple[bool, ParsedProductData | None, str | None]:
        """解析页面

        Args:
            html: HTML 内容
            url: 页面 URL
            config: 提取配置，为 None 时使用 LLM 模式

        Returns:
            (is_product_page, parsed_data, error)
        """
        if config is None or config.mode == ExtractionMode.LLM:
            return await self.parse_with_llm(
                html, url, config.prompt if config else None
            )
        else:
            return self.parse_with_selector(html, config)

    def _clean_html(self, html: str) -> str:
        """清理 HTML，移除无关内容

        Args:
            html: 原始 HTML

        Returns:
            清理后的 HTML
        """
        soup = BeautifulSoup(html, "html.parser")

        # 移除脚本和样式
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()

        # 移除注释
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
            comment.extract()

        # 移除常见的无关元素
        for selector in [
            "header",
            "footer",
            "nav",
            ".nav",
            ".header",
            ".footer",
            ".sidebar",
            ".ad",
            ".advertisement",
            "#cookie-banner",
            ".cookie-notice",
        ]:
            for elem in soup.select(selector):
                elem.decompose()

        # 获取文本内容，保留一定的结构
        # 只保留主要内容区域
        main_content = soup.select_one("main, #main, .main, article, .product, .product-detail")
        if main_content:
            return str(main_content)

        return str(soup)

    def extract_links(
        self, html: str, base_url: str, link_pattern: str | None = None
    ) -> list[str]:
        """从页面中提取链接

        Args:
            html: HTML 内容
            base_url: 基础 URL（用于处理相对路径）
            link_pattern: 链接过滤模式（正则或 glob）

        Returns:
            链接列表
        """
        from urllib.parse import urljoin, urlparse

        soup = BeautifulSoup(html, "html.parser")
        links = set()
        base_domain = urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"]

            # 跳过锚点和 JavaScript
            if href.startswith("#") or href.startswith("javascript:"):
                continue

            # 处理相对路径
            full_url = urljoin(base_url, href)

            # 只保留同域名的链接
            parsed = urlparse(full_url)
            if parsed.netloc != base_domain:
                continue

            # 移除锚点
            full_url = full_url.split("#")[0]

            # 应用链接过滤
            if link_pattern:
                if not self._match_pattern(parsed.path, link_pattern):
                    continue

            links.add(full_url)

        return list(links)

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """检查路径是否匹配模式

        Args:
            path: URL 路径
            pattern: 匹配模式（支持 glob 和正则）

        Returns:
            是否匹配
        """
        import fnmatch

        # 尝试作为 glob 模式匹配
        if fnmatch.fnmatch(path, pattern):
            return True

        # 尝试作为正则表达式匹配
        try:
            if re.search(pattern, path):
                return True
        except re.error:
            pass

        return False
