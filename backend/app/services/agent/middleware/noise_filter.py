"""噪音过滤中间件

过滤和截断工具执行的冗长输出，避免干扰模型注意力。

主要功能：
1. 截断过长的工具输出
2. 过滤噪音模式（通用 + 电商场景）
3. 压缩 JSON 格式输出
4. 截断过长的商品描述
"""

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langgraph.prebuilt.tool_node import ToolCallRequest, ToolCallWrapper

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("middleware.noise_filter")

# ==================== 通用噪音模式（代码执行类 Agent）====================
GENERIC_NOISE_PATTERNS = [
    # npm/yarn 日志
    r"npm WARN.*\n",
    r"npm notice.*\n",
    r"yarn warn.*\n",
    # pip 日志
    r"Collecting [\w\-\.]+.*\n",
    r"Downloading [\w\-\.]+.*\n",
    r"Installing collected packages.*\n",
    r"Successfully installed.*\n",
    # 进度条
    r"\[=+>?\s*\].*\n",
    r"\d+%\|[█▓▒░ ]+\|.*\n",
    # Docker 日志
    r"Pulling from.*\n",
    r"Digest: sha256:.*\n",
    r"Status: Downloaded.*\n",
    # Git 日志
    r"remote: Counting objects.*\n",
    r"remote: Compressing objects.*\n",
    r"Receiving objects:.*\n",
    r"Resolving deltas:.*\n",
    # 空行连续
    r"\n{3,}",
]

# ==================== 电商场景配置 ====================
# 商品描述最大长度（单个商品）
MAX_PRODUCT_DESCRIPTION_LENGTH = 300
# 商品列表最大展示数量（超出后压缩）
MAX_PRODUCTS_IN_LIST = 5
# 商品摘要最大长度
MAX_PRODUCT_SUMMARY_LENGTH = 150


class NoiseFilterMiddleware(AgentMiddleware):
    """噪音过滤中间件

    过滤/截断工具执行的冗长输出，主要功能：
    1. 移除匹配噪音模式的内容（如 npm/pip 安装日志）
    2. 压缩 JSON 格式输出（电商场景：商品描述截断、列表压缩）
    3. 截断超过最大长度的输出
    4. 添加截断标记提示用户

    配置：
    - AGENT_NOISE_FILTER_ENABLED: 是否启用
    - AGENT_NOISE_FILTER_MAX_CHARS: 最大输出字符数
    """

    def __init__(
        self,
        enabled: bool = True,
        max_output_chars: int = 2000,
        truncation_marker: str = "\n\n... [已截断，原始输出共 {total} 字符]",
        noise_patterns: list[str] | None = None,
        preserve_head_chars: int = 500,
        preserve_tail_chars: int = 1000,
        compress_json: bool = True,
        max_product_description: int = MAX_PRODUCT_DESCRIPTION_LENGTH,
        max_products_in_list: int = MAX_PRODUCTS_IN_LIST,
    ) -> None:
        """初始化噪音过滤中间件

        Args:
            enabled: 是否启用过滤
            max_output_chars: 最大输出字符数
            truncation_marker: 截断标记模板，支持 {total} 占位符
            noise_patterns: 噪音模式列表（正则表达式），None 则使用默认模式
            preserve_head_chars: 截断时保留头部字符数
            preserve_tail_chars: 截断时保留尾部字符数
            compress_json: 是否压缩 JSON 格式输出（电商场景）
            max_product_description: 商品描述最大长度
            max_products_in_list: 商品列表最大展示数量
        """
        super().__init__()
        self.enabled = enabled
        self.max_output_chars = max_output_chars
        self.truncation_marker = truncation_marker
        self.noise_patterns = noise_patterns or GENERIC_NOISE_PATTERNS
        self.preserve_head_chars = preserve_head_chars
        self.preserve_tail_chars = preserve_tail_chars
        self.compress_json = compress_json
        self.max_product_description = max_product_description
        self.max_products_in_list = max_products_in_list

        # 预编译正则表达式
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.noise_patterns
        ]

        logger.debug(
            "NoiseFilterMiddleware 初始化",
            enabled=enabled,
            max_output_chars=max_output_chars,
            pattern_count=len(self.noise_patterns),
            compress_json=compress_json,
        )

    def _remove_noise(self, text: str) -> str:
        """移除噪音内容（通用正则模式）"""
        for pattern in self._compiled_patterns:
            text = pattern.sub("", text)
        return text

    def _truncate_string(self, text: str, max_length: int, suffix: str = "...") -> str:
        """截断字符串到指定长度"""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

    def _compress_product(self, product: dict[str, Any]) -> dict[str, Any]:
        """压缩单个商品数据，截断过长字段"""
        compressed = product.copy()

        # 截断商品描述
        if "description" in compressed and isinstance(compressed["description"], str):
            compressed["description"] = self._truncate_string(
                compressed["description"], self.max_product_description
            )

        # 截断商品摘要
        if "summary" in compressed and isinstance(compressed["summary"], str):
            compressed["summary"] = self._truncate_string(
                compressed["summary"], MAX_PRODUCT_SUMMARY_LENGTH
            )

        # 截断 page_content（知识库场景）
        if "content" in compressed and isinstance(compressed["content"], str):
            compressed["content"] = self._truncate_string(
                compressed["content"], self.max_product_description
            )

        return compressed

    def _compress_product_list(self, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """压缩商品列表，限制数量并截断每个商品"""
        if len(products) <= self.max_products_in_list:
            return [self._compress_product(p) for p in products]

        # 超出限制，保留前 N 个，添加省略标记
        compressed = [self._compress_product(p) for p in products[: self.max_products_in_list]]
        compressed.append({
            "_truncated": True,
            "_message": f"还有 {len(products) - self.max_products_in_list} 个商品未显示",
            "_total_count": len(products),
        })
        return compressed

    def _compress_json_output(self, output: str) -> str:
        """压缩 JSON 格式输出（电商场景专用）

        处理策略：
        1. 尝试解析为 JSON
        2. 如果是商品列表，压缩列表并截断描述
        3. 如果是单个商品，截断描述
        4. 重新序列化为紧凑格式（无缩进）
        """
        if not self.compress_json:
            return output

        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            # 不是 JSON，返回原样
            return output

        compressed = False

        # 处理商品列表（顶层是列表）
        if isinstance(data, list) and data and isinstance(data[0], dict):
            if any(key in data[0] for key in ["id", "name", "price", "product_id"]):
                data = self._compress_product_list(data)
                compressed = True

        # 处理包含 products 字段的对象
        elif isinstance(data, dict):
            if "products" in data and isinstance(data["products"], list):
                data["products"] = self._compress_product_list(data["products"])
                compressed = True
            # 单个商品对象
            elif any(key in data for key in ["description", "summary", "content"]):
                data = self._compress_product(data)
                compressed = True

        if compressed:
            # 使用紧凑格式重新序列化
            return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

        return output

    def _truncate(self, text: str) -> str:
        """截断过长文本，保留头尾"""
        original_len = len(text)
        if original_len <= self.max_output_chars:
            return text

        # 保留头部 + 截断标记 + 尾部
        head = text[: self.preserve_head_chars]
        tail = text[-self.preserve_tail_chars :]
        marker = self.truncation_marker.format(total=original_len)

        return f"{head}{marker}\n\n{tail}"

    def _filter_output(self, output: str) -> str:
        """过滤并截断输出

        处理流程：
        1. 压缩 JSON 格式输出（电商场景：商品描述截断、列表压缩）
        2. 移除噪音模式（通用：npm/pip/git 等日志）
        3. 截断过长输出
        """
        if not output:
            return output

        # 1. 压缩 JSON 格式输出（电商场景）
        compressed = self._compress_json_output(output)

        # 2. 移除噪音模式（通用场景）
        cleaned = self._remove_noise(compressed)

        # 3. 截断过长输出
        truncated = self._truncate(cleaned)

        return truncated

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolCallWrapper]],
    ) -> ToolCallWrapper:
        """包装工具调用，过滤输出"""
        result = await handler(request)

        if not self.enabled:
            return result

        # 获取工具输出
        output = getattr(result, "output", None)
        if not isinstance(output, str):
            return result

        original_len = len(output)
        filtered = self._filter_output(output)
        filtered_len = len(filtered)

        # 如果有变化，记录日志
        if filtered_len < original_len:
            logger.debug(
                "工具输出已过滤",
                tool_name=request.name,
                original_chars=original_len,
                filtered_chars=filtered_len,
                reduction_pct=round((1 - filtered_len / original_len) * 100, 1),
            )

            # 创建新的 ToolCallWrapper 替换输出
            return ToolCallWrapper(
                tool_call_id=result.tool_call_id,
                name=result.name,
                output=filtered,
                error=result.error,
            )

        return result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolCallWrapper],
    ) -> ToolCallWrapper:
        """同步版本"""
        result = handler(request)

        if not self.enabled:
            return result

        output = getattr(result, "output", None)
        if not isinstance(output, str):
            return result

        original_len = len(output)
        filtered = self._filter_output(output)
        filtered_len = len(filtered)

        if filtered_len < original_len:
            logger.debug(
                "工具输出已过滤（同步）",
                tool_name=request.name,
                original_chars=original_len,
                filtered_chars=filtered_len,
            )

            return ToolCallWrapper(
                tool_call_id=result.tool_call_id,
                name=result.name,
                output=filtered,
                error=result.error,
            )

        return result
