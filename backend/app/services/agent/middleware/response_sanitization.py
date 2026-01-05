"""响应清洗中间件

负责检测和处理模型返回的异常响应格式，确保用户始终看到友好的内容。
"""

import re
from collections.abc import Awaitable, Callable

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import AIMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("middleware.response_sanitization")


class ResponseSanitizationMiddleware(AgentMiddleware):
    """响应清洗中间件

    检测并处理模型返回的异常格式响应（如格式错误的 function calling）。
    某些模型虽然声称支持 function calling，但可能返回非标准格式的内容，
    这个中间件会自动检测并替换为用户友好的消息。

    功能：
    1. 检测异常的 function call 格式
    2. 替换为用户友好的错误提示
    3. 记录异常日志用于监控
    4. 支持配置开关

    Example:
        ```python
        from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware

        agent = create_agent(
            model="gpt-4",
            tools=[search_products],
            middleware=[
                LoggingMiddleware(),
                ResponseSanitizationMiddleware(),  # 启用响应清洗
            ],
        )
        ```
    """

    # 统计计数器（类变量）
    _malformed_count = 0
    _total_responses = 0

    def __init__(
        self,
        enabled: bool = True,
        custom_fallback_message: str | None = None,
    ):
        """初始化响应清洗中间件

        Args:
            enabled: 是否启用清洗功能
            custom_fallback_message: 自定义的降级消息（可选）
        """
        self.enabled = enabled
        self.custom_fallback_message = custom_fallback_message

        logger.debug(
            "ResponseSanitizationMiddleware 初始化完成",
            enabled=enabled,
        )

    @staticmethod
    def _is_malformed_function_call(content: str) -> bool:
        """检测是否为格式错误的 function call 响应

        检测模式：
        - [function:tool_name:id{...}]
        - [tool:tool_name{...}]
        - <function>...</function>
        - {"function": {"name": ...}}
        - [{"name": "tool_name", "parameters": {...}}]

        Args:
            content: 模型返回的文本内容

        Returns:
            True 如果检测到异常格式
        """
        if not content or len(content.strip()) < 10:
            return False

        content_stripped = content.strip()

        # 检测常见的异常模式
        patterns = [
            # [function:xxx:1{...}]
            r"^\[function:[^:]+:\d+\{",
            # [function:xxx{...}]
            r"^\[function:[^\]]+\{",
            # [tool:xxx]
            r"^\[tool:[^\]]+\]",
            # <function>xxx</function>
            r"^<function[^>]*>",
            # {"function": {"name": ...}} (纯 JSON，不是正常对话)
            r'^{[\s\n]*"function"[\s\n]*:[\s\n]*{[\s\n]*"name"',
            # [{"name": "tool_name", "parameters": {...}, ...}]
            r'^\[\s*\{\s*"name"\s*:\s*"[^"]+"\s*,\s*"parameters"\s*:',
            # [uuid]:0{...}<|tool_calls_section_end|>
            r"^\[[a-f0-9-]{30,}\]:\d+\{.*\}<\|",
        ]

        for pattern in patterns:
            if re.match(pattern, content_stripped, re.IGNORECASE | re.DOTALL):
                return True

        # 额外检测：如果整个响应就是一个 JSON 对象且包含 function/tool 关键字
        if content_stripped.startswith("{") and content_stripped.endswith("}"):
            if '"function"' in content_stripped or '"tool_call"' in content_stripped:
                # 但要排除正常的结构化输出（通常会有多个字段）
                if content_stripped.count('"') < 10:  # 简单的结构化输出判断
                    return True

        # 额外检测：JSON 数组格式的工具调用
        # [{"name": "xxx", "parameters": {...}, "id": "xxx"}]
        if content_stripped.startswith("[") and content_stripped.endswith("]"):
            # 检查是否包含工具调用的特征字段
            if (
                '"name"' in content_stripped
                and '"parameters"' in content_stripped
                and
                # 确保不是正常的商品列表等
                '"id"' in content_stripped
                and
                # 排除正常的产品数据（通常包含 title, description 等）
                '"title"' not in content_stripped
                and '"description"' not in content_stripped
            ):
                return True

        # 额外检测：包含特殊的工具调用标记
        # <|tool_calls_section_end|>, <|tool_sep|>, <|tool_start|> 等
        if (
            "<|tool" in content_stripped
            or "|tool_" in content_stripped
            or "tool_calls_section" in content_stripped
        ):
            return True

        return False

    def _get_fallback_message(self, original_content: str) -> str:
        """生成友好的降级消息

        Args:
            original_content: 原始的异常内容

        Returns:
            用户友好的错误消息
        """
        # 如果有自定义消息，优先使用
        if self.custom_fallback_message:
            return self.custom_fallback_message

        # 使用默认友好消息
        return (
            "抱歉，我在处理您的请求时遇到了一些技术问题。😅\n\n"
            "可能的原因：\n"
            "• 当前 AI 模型暂时不稳定\n"
            "• 工具调用格式需要调整\n\n"
            "建议您：\n"
            "1. 稍后重试一次\n"
            "2. 或者换一个问法试试\n"
            "3. 如果问题持续，请联系技术支持\n\n"
            "我们会持续改进体验！"
        )

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步包装模型调用，在响应后进行清洗处理"""

        # 如果禁用，直接透传
        if not self.enabled:
            return await handler(request)

        # 调用模型
        response = await handler(request)

        ResponseSanitizationMiddleware._total_responses += 1

        # 检查响应中的每条消息
        sanitized = False
        for i, msg in enumerate(response.result):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content

                # 如果是列表（某些模型会返回列表），转为字符串
                if isinstance(content, list):
                    content = "".join(str(x) for x in content)

                # 检测异常格式
                if self._is_malformed_function_call(content):
                    ResponseSanitizationMiddleware._malformed_count += 1

                    logger.warning(
                        "检测到异常 function call 格式，已替换为友好消息",
                        model=getattr(request.model, "model_name", "unknown"),
                        provider=settings.LLM_PROVIDER,
                        content_preview=content[:100],
                        malformed_count=ResponseSanitizationMiddleware._malformed_count,
                        total_responses=ResponseSanitizationMiddleware._total_responses,
                        malformed_rate=f"{ResponseSanitizationMiddleware._malformed_count / ResponseSanitizationMiddleware._total_responses * 100:.2f}%",
                    )

                    # 替换为友好消息
                    fallback_msg = self._get_fallback_message(content)

                    # 创建新的 AIMessage，保留原有的元数据
                    response.result[i] = AIMessage(
                        content=fallback_msg,
                        additional_kwargs=(
                            msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}
                        ),
                        response_metadata=(
                            msg.response_metadata if hasattr(msg, "response_metadata") else {}
                        ),
                    )

                    sanitized = True

        if sanitized:
            logger.info(
                "响应已清洗",
                sanitized_count=1,
            )

        return response

    @classmethod
    def get_statistics(cls) -> dict[str, int | float]:
        """获取统计信息

        Returns:
            包含异常响应统计的字典
        """
        return {
            "total_responses": cls._total_responses,
            "malformed_count": cls._malformed_count,
            "malformed_rate": (
                cls._malformed_count / cls._total_responses * 100
                if cls._total_responses > 0
                else 0.0
            ),
        }

    @classmethod
    def reset_statistics(cls) -> None:
        """重置统计计数器"""
        cls._total_responses = 0
        cls._malformed_count = 0
        logger.info("响应清洗统计已重置")
