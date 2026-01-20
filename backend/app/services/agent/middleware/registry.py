"""中间件注册表 - 声明式配置，顺序即执行顺序

使用方式：
    from app.services.agent.middleware.registry import build_middlewares, build_middlewares_for_agent

    # 传统方式（兼容）
    middlewares = build_middlewares(mode="natural", model=model)

    # 基于 Agent 配置（推荐）
    from app.schemas.agent import AgentConfig
    middlewares = build_middlewares_for_agent(config, model)

扩展方式：
    在 _get_middleware_specs() 中添加新的 MiddlewareSpec 即可
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("middleware.registry")


@dataclass
class MiddlewareSpec:
    """中间件规格定义

    Attributes:
        name: 中间件名称（用于日志）
        order: 执行顺序（数字越小越先执行）
        factory: 中间件工厂函数，返回中间件实例或 None
        enabled: 是否启用（可以是 bool 或返回 bool 的 callable）
        dependencies: 依赖的中间件名称列表（向后扩展预留）
    """

    name: str
    order: int
    factory: Callable[..., Any | None]
    enabled: bool | Callable[[], bool] = True
    dependencies: list[str] = field(default_factory=list)

    def is_enabled(self) -> bool:
        """检查是否启用"""
        if callable(self.enabled):
            return self.enabled()
        return self.enabled

    def create(self) -> Any | None:
        """创建中间件实例"""
        try:
            return self.factory()
        except Exception as e:
            logger.warning(f"{self.name} 初始化失败", error=str(e))
            return None


# ========== 中间件执行顺序表（一目了然） ==========
#
# Order │ 名称                     │ 说明
# ──────┼──────────────────────────┼────────────────────
#   10  │ MemoryOrchestration      │ 记忆注入 + 异步写入
#   20  │ ResponseSanitization     │ 响应内容安全过滤
#   30  │ SSE                      │ LLM 调用事件推送
#   40  │ TodoList + TodoBroadcast │ 任务规划 + 广播
#   50  │ SequentialToolExecution  │ 工具串行执行
#   55  │ NoiseFilter              │ 工具输出噪音过滤
#   60  │ Logging                  │ 日志记录
#   70  │ ToolRetry                │ 工具重试
#   80  │ ToolCallLimit            │ 工具调用限制
#   85  │ SlidingWindow            │ 滑动窗口裁剪
#   90  │ Summarization            │ 上下文压缩摘要
#  100  │ StrictMode               │ 严格模式检查
# ──────┴──────────────────────────┴────────────────────


def _get_middleware_specs(mode: str, model: Any) -> list[MiddlewareSpec]:
    """获取中间件规格列表

    Args:
        mode: 聊天模式（natural/free/strict）
        model: LLM 模型实例（部分中间件需要）

    Returns:
        中间件规格列表
    """
    from langchain.agents.middleware.summarization import SummarizationMiddleware
    from langchain.agents.middleware.todo import TodoListMiddleware
    from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
    from langchain.agents.middleware.tool_retry import ToolRetryMiddleware

    from app.services.agent.middleware.llm_call_sse import SSEMiddleware
    from app.services.agent.middleware.logging import LoggingMiddleware
    from app.services.agent.middleware.noise_filter import NoiseFilterMiddleware
    from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware
    from app.services.agent.middleware.sequential_tools import SequentialToolExecutionMiddleware
    from app.services.agent.middleware.sliding_window import SlidingWindowMiddleware
    from app.services.agent.middleware.strict_mode import StrictModeMiddleware
    from app.services.agent.middleware.summarization_broadcast import (
        SummarizationBroadcastMiddleware,
    )
    from app.services.agent.middleware.todo_broadcast import TodoBroadcastMiddleware
    from app.services.memory.middleware.orchestration import MemoryOrchestrationMiddleware

    # ========== 工厂函数定义 ==========

    def _build_tool_limit_middleware():
        """构建工具调用限制中间件"""
        limit_kwargs: dict[str, Any] = {"exit_behavior": settings.AGENT_TOOL_LIMIT_EXIT_BEHAVIOR}
        if settings.AGENT_TOOL_LIMIT_THREAD is not None:
            limit_kwargs["thread_limit"] = settings.AGENT_TOOL_LIMIT_THREAD
        if settings.AGENT_TOOL_LIMIT_RUN is not None:
            limit_kwargs["run_limit"] = settings.AGENT_TOOL_LIMIT_RUN
        if "thread_limit" not in limit_kwargs and "run_limit" not in limit_kwargs:
            return None
        return ToolCallLimitMiddleware(**limit_kwargs)

    def _build_todo_middlewares():
        """构建 TODO 中间件列表"""
        todo_kwargs: dict[str, Any] = {}
        if settings.AGENT_TODO_SYSTEM_PROMPT:
            todo_kwargs["system_prompt"] = settings.AGENT_TODO_SYSTEM_PROMPT
        if settings.AGENT_TODO_TOOL_DESCRIPTION:
            todo_kwargs["tool_description"] = settings.AGENT_TODO_TOOL_DESCRIPTION
        return [TodoListMiddleware(**todo_kwargs), TodoBroadcastMiddleware()]

    def _build_sliding_window_middleware():
        """构建滑动窗口中间件"""
        return SlidingWindowMiddleware(
            strategy=settings.AGENT_SLIDING_WINDOW_STRATEGY,
            max_messages=settings.AGENT_SLIDING_WINDOW_MAX_MESSAGES,
            max_tokens=settings.AGENT_SLIDING_WINDOW_MAX_TOKENS,
        )

    def _build_noise_filter_middleware():
        """构建噪音过滤中间件"""
        return NoiseFilterMiddleware(
            enabled=settings.AGENT_NOISE_FILTER_ENABLED,
            max_output_chars=settings.AGENT_NOISE_FILTER_MAX_CHARS,
            preserve_head_chars=settings.AGENT_NOISE_FILTER_PRESERVE_HEAD,
            preserve_tail_chars=settings.AGENT_NOISE_FILTER_PRESERVE_TAIL,
        )

    def _build_summarization_middleware():
        """构建上下文压缩中间件（增强版：支持多触发条件）"""
        from langchain.chat_models import init_chat_model

        # 构建触发条件列表
        trigger_conditions: list[tuple[str, int | float]] = []
        if settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES > 0:
            trigger_conditions.append(("messages", settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES))
        if settings.AGENT_SUMMARIZATION_TRIGGER_TOKENS > 0:
            trigger_conditions.append(("tokens", settings.AGENT_SUMMARIZATION_TRIGGER_TOKENS))
        if settings.AGENT_SUMMARIZATION_TRIGGER_FRACTION > 0:
            trigger_conditions.append(("fraction", settings.AGENT_SUMMARIZATION_TRIGGER_FRACTION))

        # 如果没有配置任何触发条件，使用默认的消息数触发
        if not trigger_conditions:
            trigger_conditions.append(("messages", 50))

        # 构建保留策略
        if settings.AGENT_SUMMARIZATION_KEEP_STRATEGY == "tokens":
            keep = ("tokens", settings.AGENT_SUMMARIZATION_KEEP_TOKENS)
        else:
            keep = ("messages", settings.AGENT_SUMMARIZATION_KEEP_MESSAGES)

        # 摘要模型（可使用独立的轻量级模型）
        summarization_model = model
        if settings.AGENT_SUMMARIZATION_MODEL:
            try:
                summarization_model = init_chat_model(settings.AGENT_SUMMARIZATION_MODEL)
            except Exception as e:
                logger.warning(f"摘要模型初始化失败，使用主模型", error=str(e))

        inner = SummarizationMiddleware(
            model=summarization_model,
            trigger=trigger_conditions if len(trigger_conditions) > 1 else trigger_conditions[0],
            keep=keep,
            trim_tokens_to_summarize=settings.AGENT_SUMMARIZATION_TRIM_TOKENS,
        )
        return SummarizationBroadcastMiddleware(inner)

    def _build_strict_mode_middleware():
        """构建严格模式中间件"""
        from app.services.agent.core.policy import get_policy

        return StrictModeMiddleware(policy=get_policy(mode))

    # ========== 中间件规格列表（按 order 排序后依次构建） ==========

    return [
        # Order 10: 记忆编排（最先执行，注入记忆上下文）
        MiddlewareSpec(
            name="MemoryOrchestration",
            order=10,
            enabled=settings.MEMORY_ENABLED and settings.MEMORY_ORCHESTRATION_ENABLED,
            factory=MemoryOrchestrationMiddleware,
        ),
        # Order 20: 响应安全过滤
        MiddlewareSpec(
            name="ResponseSanitization",
            order=20,
            enabled=True,
            factory=lambda: ResponseSanitizationMiddleware(
                enabled=settings.RESPONSE_SANITIZATION_ENABLED,
                custom_fallback_message=settings.RESPONSE_SANITIZATION_CUSTOM_MESSAGE,
            ),
        ),
        # Order 30: SSE 事件推送（llm.call.start/end）
        MiddlewareSpec(
            name="SSE",
            order=30,
            enabled=True,
            factory=SSEMiddleware,
        ),
        # Order 40: TODO 任务规划 + 广播
        MiddlewareSpec(
            name="TodoList",
            order=40,
            enabled=settings.AGENT_TODO_ENABLED,
            factory=_build_todo_middlewares,
        ),
        # Order 50: 工具串行执行
        MiddlewareSpec(
            name="SequentialToolExecution",
            order=50,
            enabled=settings.AGENT_SERIALIZE_TOOLS,
            factory=SequentialToolExecutionMiddleware,
        ),
        # Order 55: 噪音过滤
        MiddlewareSpec(
            name="NoiseFilter",
            order=55,
            enabled=settings.AGENT_NOISE_FILTER_ENABLED,
            factory=_build_noise_filter_middleware,
        ),
        # Order 60: 日志记录
        MiddlewareSpec(
            name="Logging",
            order=60,
            enabled=True,
            factory=LoggingMiddleware,
        ),
        # Order 70: 工具重试
        MiddlewareSpec(
            name="ToolRetry",
            order=70,
            enabled=settings.AGENT_TOOL_RETRY_ENABLED,
            factory=lambda: ToolRetryMiddleware(
                max_retries=settings.AGENT_TOOL_RETRY_MAX_RETRIES,
                backoff_factor=settings.AGENT_TOOL_RETRY_BACKOFF_FACTOR,
                initial_delay=settings.AGENT_TOOL_RETRY_INITIAL_DELAY,
                max_delay=settings.AGENT_TOOL_RETRY_MAX_DELAY,
            ),
        ),
        # Order 80: 工具调用限制
        MiddlewareSpec(
            name="ToolCallLimit",
            order=80,
            enabled=settings.AGENT_TOOL_LIMIT_ENABLED,
            factory=_build_tool_limit_middleware,
        ),
        # Order 85: 滑动窗口裁剪
        MiddlewareSpec(
            name="SlidingWindow",
            order=85,
            enabled=settings.AGENT_SLIDING_WINDOW_ENABLED,
            factory=_build_sliding_window_middleware,
        ),
        # Order 90: 上下文压缩摘要
        MiddlewareSpec(
            name="Summarization",
            order=90,
            enabled=settings.AGENT_SUMMARIZATION_ENABLED,
            factory=_build_summarization_middleware,
        ),
        # Order 100: 严格模式检查（最后执行）
        MiddlewareSpec(
            name="StrictMode",
            order=100,
            enabled=mode == "strict",
            factory=_build_strict_mode_middleware,
        ),
    ]


def build_middlewares(mode: str, model: Any) -> list[Any]:
    """构建中间件链（对外接口）

    Args:
        mode: 聊天模式（natural/free/strict）
        model: LLM 模型实例

    Returns:
        中间件实例列表（按 order 排序）
    """
    specs = _get_middleware_specs(mode, model)
    middlewares: list[Any] = []

    for spec in sorted(specs, key=lambda s: s.order):
        if not spec.is_enabled():
            continue
        result = spec.create()
        if result is None:
            continue
        # 支持返回列表（如 TodoList 返回 [TodoListMiddleware, TodoBroadcastMiddleware]）
        if isinstance(result, list):
            middlewares.extend(result)
            logger.debug(f"✓ {spec.name} (order={spec.order})", count=len(result))
        else:
            middlewares.append(result)
            logger.debug(f"✓ {spec.name} (order={spec.order})")

    return middlewares


def build_middlewares_for_agent(config: "AgentConfig", model: Any) -> list[Any]:
    """根据 Agent 配置构建中间件链

    支持 Agent 级别的中间件配置：
    1. 开关配置：是否启用某个中间件
    2. 参数配置：中间件的详细参数（滑动窗口、摘要、噪音过滤）

    配置继承链：Agent 配置 > 全局 settings

    Args:
        config: Agent 运行时配置
        model: LLM 模型实例

    Returns:
        中间件实例列表（按 order 排序）
    """
    from langchain.agents.middleware.summarization import SummarizationMiddleware
    from langchain.agents.middleware.todo import TodoListMiddleware
    from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
    from langchain.agents.middleware.tool_retry import ToolRetryMiddleware

    from app.services.agent.middleware.llm_call_sse import SSEMiddleware
    from app.services.agent.middleware.logging import LoggingMiddleware
    from app.services.agent.middleware.noise_filter import NoiseFilterMiddleware
    from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware
    from app.services.agent.middleware.sequential_tools import SequentialToolExecutionMiddleware
    from app.services.agent.middleware.sliding_window import SlidingWindowMiddleware
    from app.services.agent.middleware.strict_mode import StrictModeMiddleware
    from app.services.agent.middleware.summarization_broadcast import SummarizationBroadcastMiddleware
    from app.services.agent.middleware.todo_broadcast import TodoBroadcastMiddleware
    from app.services.memory.middleware.orchestration import MemoryOrchestrationMiddleware

    mode = config.mode
    middlewares: list[Any] = []
    flags = config.middleware_flags

    # 辅助函数：获取配置值（优先 Agent 配置，fallback 到全局 settings）
    def _get(key: str, default: Any = None) -> Any:
        if flags:
            value = getattr(flags, key, None)
            if value is not None:
                return value
        return getattr(settings, f"AGENT_{key.upper()}", default)

    def _is_enabled(flag_key: str, settings_key: str) -> bool:
        if flags:
            value = getattr(flags, flag_key, None)
            if value is not None:
                return value
        return getattr(settings, settings_key, False)

    # ========== 构建中间件列表（按 order 排序） ==========

    # Order 10: 记忆编排
    if _is_enabled("memory_enabled", "MEMORY_ENABLED") and settings.MEMORY_ORCHESTRATION_ENABLED:
        middlewares.append(MemoryOrchestrationMiddleware())
        logger.debug("✓ MemoryOrchestration (order=10)", agent_id=config.agent_id)

    # Order 20: 响应安全过滤
    middlewares.append(ResponseSanitizationMiddleware(
        enabled=settings.RESPONSE_SANITIZATION_ENABLED,
        custom_fallback_message=settings.RESPONSE_SANITIZATION_CUSTOM_MESSAGE,
    ))
    logger.debug("✓ ResponseSanitization (order=20)", agent_id=config.agent_id)

    # Order 30: SSE 事件推送
    middlewares.append(SSEMiddleware())
    logger.debug("✓ SSE (order=30)", agent_id=config.agent_id)

    # Order 40: TODO 任务规划
    if _is_enabled("todo_enabled", "AGENT_TODO_ENABLED"):
        todo_kwargs: dict[str, Any] = {}
        if settings.AGENT_TODO_SYSTEM_PROMPT:
            todo_kwargs["system_prompt"] = settings.AGENT_TODO_SYSTEM_PROMPT
        if settings.AGENT_TODO_TOOL_DESCRIPTION:
            todo_kwargs["tool_description"] = settings.AGENT_TODO_TOOL_DESCRIPTION
        middlewares.append(TodoListMiddleware(**todo_kwargs))
        middlewares.append(TodoBroadcastMiddleware())
        logger.debug("✓ TodoList (order=40)", agent_id=config.agent_id)

    # Order 50: 工具串行执行
    if settings.AGENT_SERIALIZE_TOOLS:
        middlewares.append(SequentialToolExecutionMiddleware())
        logger.debug("✓ SequentialToolExecution (order=50)", agent_id=config.agent_id)

    # Order 55: 噪音过滤（支持 Agent 级配置）
    if _is_enabled("noise_filter_enabled", "AGENT_NOISE_FILTER_ENABLED"):
        middlewares.append(NoiseFilterMiddleware(
            enabled=True,
            max_output_chars=_get("noise_filter_max_chars", settings.AGENT_NOISE_FILTER_MAX_CHARS),
            preserve_head_chars=_get("noise_filter_preserve_head", settings.AGENT_NOISE_FILTER_PRESERVE_HEAD),
            preserve_tail_chars=_get("noise_filter_preserve_tail", settings.AGENT_NOISE_FILTER_PRESERVE_TAIL),
        ))
        logger.debug("✓ NoiseFilter (order=55)", agent_id=config.agent_id)

    # Order 60: 日志记录
    middlewares.append(LoggingMiddleware())
    logger.debug("✓ Logging (order=60)", agent_id=config.agent_id)

    # Order 70: 工具重试
    if _is_enabled("tool_retry_enabled", "AGENT_TOOL_RETRY_ENABLED"):
        middlewares.append(ToolRetryMiddleware(
            max_retries=settings.AGENT_TOOL_RETRY_MAX_RETRIES,
            backoff_factor=settings.AGENT_TOOL_RETRY_BACKOFF_FACTOR,
            initial_delay=settings.AGENT_TOOL_RETRY_INITIAL_DELAY,
            max_delay=settings.AGENT_TOOL_RETRY_MAX_DELAY,
        ))
        logger.debug("✓ ToolRetry (order=70)", agent_id=config.agent_id)

    # Order 80: 工具调用限制
    if _is_enabled("tool_limit_enabled", "AGENT_TOOL_LIMIT_ENABLED"):
        limit_kwargs: dict[str, Any] = {"exit_behavior": settings.AGENT_TOOL_LIMIT_EXIT_BEHAVIOR}
        if settings.AGENT_TOOL_LIMIT_THREAD is not None:
            limit_kwargs["thread_limit"] = settings.AGENT_TOOL_LIMIT_THREAD
        if settings.AGENT_TOOL_LIMIT_RUN is not None:
            limit_kwargs["run_limit"] = settings.AGENT_TOOL_LIMIT_RUN
        if "thread_limit" in limit_kwargs or "run_limit" in limit_kwargs:
            middlewares.append(ToolCallLimitMiddleware(**limit_kwargs))
            logger.debug("✓ ToolCallLimit (order=80)", agent_id=config.agent_id)

    # Order 85: 滑动窗口（支持 Agent 级配置）
    if _is_enabled("sliding_window_enabled", "AGENT_SLIDING_WINDOW_ENABLED"):
        middlewares.append(SlidingWindowMiddleware(
            strategy=_get("sliding_window_strategy", settings.AGENT_SLIDING_WINDOW_STRATEGY),
            max_messages=_get("sliding_window_max_messages", settings.AGENT_SLIDING_WINDOW_MAX_MESSAGES),
            max_tokens=_get("sliding_window_max_tokens", settings.AGENT_SLIDING_WINDOW_MAX_TOKENS),
        ))
        logger.debug("✓ SlidingWindow (order=85)", agent_id=config.agent_id)

    # Order 90: 上下文压缩（支持 Agent 级配置）
    if _is_enabled("summarization_enabled", "AGENT_SUMMARIZATION_ENABLED"):
        from langchain.chat_models import init_chat_model

        # 构建触发条件
        trigger_messages = _get("summarization_trigger_messages", settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES)
        trigger_tokens = _get("summarization_trigger_tokens", settings.AGENT_SUMMARIZATION_TRIGGER_TOKENS)

        trigger_conditions: list[tuple[str, int | float]] = []
        if trigger_messages and trigger_messages > 0:
            trigger_conditions.append(("messages", trigger_messages))
        if trigger_tokens and trigger_tokens > 0:
            trigger_conditions.append(("tokens", trigger_tokens))
        if not trigger_conditions:
            trigger_conditions.append(("messages", 50))

        # 构建保留策略
        keep_strategy = _get("summarization_keep_strategy", settings.AGENT_SUMMARIZATION_KEEP_STRATEGY)
        if keep_strategy == "tokens":
            keep = ("tokens", _get("summarization_keep_tokens", settings.AGENT_SUMMARIZATION_KEEP_TOKENS))
        else:
            keep = ("messages", _get("summarization_keep_messages", settings.AGENT_SUMMARIZATION_KEEP_MESSAGES))

        # 摘要模型
        summarization_model_name = _get("summarization_model", settings.AGENT_SUMMARIZATION_MODEL)
        summarization_model = model
        if summarization_model_name:
            try:
                summarization_model = init_chat_model(summarization_model_name)
            except Exception as e:
                logger.warning("摘要模型初始化失败，使用主模型", error=str(e))

        inner = SummarizationMiddleware(
            model=summarization_model,
            trigger=trigger_conditions if len(trigger_conditions) > 1 else trigger_conditions[0],
            keep=keep,
            trim_tokens_to_summarize=settings.AGENT_SUMMARIZATION_TRIM_TOKENS,
        )
        middlewares.append(SummarizationBroadcastMiddleware(inner))
        logger.debug("✓ Summarization (order=90)", agent_id=config.agent_id)

    # Order 100: 严格模式
    if mode == "strict" or _is_enabled("strict_mode_enabled", "AGENT_STRICT_MODE_ENABLED"):
        from app.services.agent.core.policy import get_policy
        middlewares.append(StrictModeMiddleware(policy=get_policy(mode)))
        logger.debug("✓ StrictMode (order=100)", agent_id=config.agent_id)

    return middlewares


if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig
