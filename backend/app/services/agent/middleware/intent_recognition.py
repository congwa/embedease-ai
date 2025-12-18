"""意图识别中间件

负责在用户输入时识别意图，并根据意图调整工具选择策略。
"""

from collections.abc import Awaitable, Callable

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.logging import get_logger
from app.schemas.intent import INTENT_TO_TOOLS, IntentType

logger = get_logger("middleware.intent_recognition")


def _get_mode_from_request(request: ModelRequest) -> str:
    """从 ModelRequest.runtime.context 获取当前聊天模式。"""
    runtime = getattr(request, "runtime", None)
    chat_context = getattr(runtime, "context", None) if runtime is not None else None
    mode = getattr(chat_context, "mode", None)
    return mode if isinstance(mode, str) else "natural"


def _get_tool_by_name(tools: list, name: str):
    for t in tools:
        if getattr(t, "name", None) == name:
            return t
    return None


class IntentRecognitionMiddleware(AgentMiddleware):
    """意图识别中间件

    在模型调用前识别用户意图，并根据意图动态调整可用工具列表。

    功能：
    1. 基于规则的快速意图识别
    2. 根据意图过滤和排序工具
    3. 在系统提示词中注入意图上下文

    Example:
        ```python
        from app.services.agent.middleware.intent_recognition import IntentRecognitionMiddleware

        agent = create_agent(
            model="gpt-4",
            tools=[search_products, compare_products, get_product_details, filter_by_price],
            middleware=[
                LoggingMiddleware(),
                IntentRecognitionMiddleware(),  # 启用意图识别
            ],
        )
        ```
    """

    def __init__(self, use_llm_intent: bool = False):
        """初始化意图识别中间件

        Args:
            use_llm_intent: 是否使用 LLM 进行意图识别（暂未实现）
        """
        self.use_llm_intent = use_llm_intent
        logger.debug("IntentRecognitionMiddleware 初始化完成", use_llm=use_llm_intent)

    def _classify_intent_by_rules(self, message: str) -> tuple[str, float]:
        """基于规则的意图分类

        Args:
            message: 用户消息

        Returns:
            (意图类型, 置信度)
        """
        message_lower = message.lower()

        # 问候语检测
        greeting_keywords = ["你好", "hello", "hi", "嗨", "您好"]
        if any(kw in message_lower for kw in greeting_keywords) and len(message) < 20:
            return IntentType.GREETING, 0.9

        # 对比意图检测
        compare_keywords = ["比较", "对比", "哪个更好", "哪个好", "对比一下", "vs"]
        if any(kw in message_lower for kw in compare_keywords):
            return IntentType.COMPARE, 0.85

        # 详情意图检测
        detail_keywords = ["详情", "详细信息", "介绍", "具体", "这款", "这个商品"]
        if any(kw in message_lower for kw in detail_keywords):
            return IntentType.DETAIL, 0.8

        # 价格过滤意图检测
        price_patterns = [
            ("元以下", IntentType.FILTER_PRICE, 0.9),
            ("元以上", IntentType.FILTER_PRICE, 0.9),
            ("预算", IntentType.FILTER_PRICE, 0.85),
            ("多少钱", IntentType.FILTER_PRICE, 0.7),
            ("价格", IntentType.FILTER_PRICE, 0.7),
        ]
        for pattern, intent, confidence in price_patterns:
            if pattern in message_lower:
                return intent, confidence

        # 推荐意图检测
        recommend_keywords = ["推荐", "建议", "帮我选", "买什么", "适合"]
        if any(kw in message_lower for kw in recommend_keywords):
            return IntentType.RECOMMEND, 0.85

        # 一般问题检测
        question_keywords = ["什么是", "为什么", "怎么", "如何", "能不能"]
        if any(kw in message_lower for kw in question_keywords):
            return IntentType.QUESTION, 0.7

        # 默认为搜索意图
        return IntentType.SEARCH, 0.6

    def _filter_tools_by_intent(self, tools: list, intent: str) -> list:
        """根据意图过滤工具

        Args:
            tools: 原始工具列表
            intent: 识别出的意图

        Returns:
            过滤后的工具列表
        """
        required_tool_names = INTENT_TO_TOOLS.get(intent, ["search_products"])

        # 如果意图不需要工具，返回空列表
        if not required_tool_names:
            return []

        # 过滤工具
        filtered_tools = [
            tool for tool in tools if getattr(tool, "name", str(tool)) in required_tool_names
        ]

        logger.debug(
            "根据意图过滤工具",
            intent=intent,
            original_count=len(tools),
            filtered_count=len(filtered_tools),
            filtered_names=[getattr(t, "name", str(t)) for t in filtered_tools],
        )

        return filtered_tools

    def _build_intent_context(self, intent: str, confidence: float) -> str:
        """构建意图上下文提示

        Args:
            intent: 意图类型
            confidence: 置信度

        Returns:
            意图上下文字符串
        """
        intent_descriptions = {
            IntentType.SEARCH: "用户想要搜索商品，请使用 search_products 工具。",
            IntentType.COMPARE: "用户想要对比商品，请先搜索商品，再使用 compare_products 工具对比。",
            IntentType.DETAIL: "用户想要了解商品详情，请使用 get_product_details 工具。",
            IntentType.FILTER_PRICE: "用户有价格预算，请使用 filter_by_price 工具过滤价格。",
            IntentType.RECOMMEND: "用户需要推荐，请综合使用搜索和过滤工具。",
            IntentType.QUESTION: "用户在询问问题，请直接回答，不需要调用工具。",
            IntentType.GREETING: "用户在打招呼，请友好回应，不需要调用工具。",
            IntentType.UNKNOWN: "意图不明确，请使用 search_products 工具尝试搜索。",
        }

        description = intent_descriptions.get(intent, "")
        return f"""
## 用户意图分析
- **识别意图**: {intent}
- **置信度**: {confidence:.2f}
- **建议策略**: {description}
"""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """在模型调用时识别意图并调整工具"""
        mode = _get_mode_from_request(request)

        # 获取最后一条用户消息
        last_human_message = None
        for msg in reversed(request.messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg
                break

        if not last_human_message:
            # 没有用户消息，直接调用
            return handler(request)

        # 识别意图
        intent, confidence = self._classify_intent_by_rules(last_human_message.content)

        logger.info(
            "意图识别完成",
            intent=intent,
            confidence=confidence,
            message_preview=last_human_message.content[:100],
        )

        # 根据意图过滤工具
        filtered_tools = self._filter_tools_by_intent(request.tools, intent)

        # strict 模式：保证 guide_user 永远可用，且绝不返回空工具列表
        if mode == "strict":
            guide_user_tool = _get_tool_by_name(request.tools, "guide_user")
            if guide_user_tool is not None:
                if intent in (IntentType.GREETING, IntentType.QUESTION):
                    filtered_tools = [guide_user_tool]
                else:
                    if not filtered_tools:
                        filtered_tools = [guide_user_tool]
                    elif guide_user_tool not in filtered_tools:
                        filtered_tools = [*filtered_tools, guide_user_tool]

        # 构建意图上下文
        intent_context = self._build_intent_context(intent, confidence)

        if mode == "strict":
            intent_context = (
                f"{intent_context}\n"
                "\n## 严格模式补充约束\n"
                "- 如果信息不足以进行检索/推荐，请优先调用 **guide_user** 工具生成澄清问题（不要直接回答）。\n"
            )

        # 修改系统提示词
        original_prompt = request.system_message.content if request.system_message else ""
        enhanced_prompt = f"{original_prompt}\n{intent_context}"

        new_system_message = SystemMessage(content=enhanced_prompt)

        # 创建新的请求
        modified_request = request.override(
            system_message=new_system_message,
            tools=filtered_tools,
        )

        logger.debug(
            "已注入意图上下文",
            intent=intent,
            tool_count=len(filtered_tools),
        )

        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步版本：在模型调用时识别意图并调整工具"""
        mode = _get_mode_from_request(request)

        # 获取最后一条用户消息
        last_human_message = None
        for msg in reversed(request.messages):
            if isinstance(msg, HumanMessage):
                last_human_message = msg
                break

        if not last_human_message:
            # 没有用户消息，直接调用
            return await handler(request)

        # 识别意图
        intent, confidence = self._classify_intent_by_rules(last_human_message.content)

        logger.info(
            "意图识别完成",
            intent=intent,
            confidence=confidence,
            message_preview=last_human_message.content[:100],
        )

        # 根据意图过滤工具
        filtered_tools = self._filter_tools_by_intent(request.tools, intent)

        # strict 模式：保证 guide_user 永远可用，且绝不返回空工具列表
        if mode == "strict":
            guide_user_tool = _get_tool_by_name(request.tools, "guide_user")
            if guide_user_tool is not None:
                if intent in (IntentType.GREETING, IntentType.QUESTION):
                    filtered_tools = [guide_user_tool]
                else:
                    if not filtered_tools:
                        filtered_tools = [guide_user_tool]
                    elif guide_user_tool not in filtered_tools:
                        filtered_tools = [*filtered_tools, guide_user_tool]

        # 构建意图上下文
        intent_context = self._build_intent_context(intent, confidence)

        if mode == "strict":
            intent_context = (
                f"{intent_context}\n"
                "\n## 严格模式补充约束\n"
                "- 如果信息不足以进行检索/推荐，请优先调用 **guide_user** 工具生成澄清问题（不要直接回答）。\n"
            )

        # 修改系统提示词
        original_prompt = request.system_message.content if request.system_message else ""
        enhanced_prompt = f"{original_prompt}\n{intent_context}"

        new_system_message = SystemMessage(content=enhanced_prompt)

        # 创建新的请求
        modified_request = request.override(
            system_message=new_system_message,
            tools=filtered_tools,
        )

        logger.debug(
            "已注入意图上下文",
            intent=intent,
            tool_count=len(filtered_tools),
        )

        return await handler(modified_request)
