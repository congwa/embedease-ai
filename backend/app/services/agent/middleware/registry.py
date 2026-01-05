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
from typing import Any

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
#   60  │ Logging                  │ 日志记录
#   70  │ ToolRetry                │ 工具重试
#   80  │ ToolCallLimit            │ 工具调用限制
#   90  │ Summarization            │ 上下文压缩
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
    from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware
    from app.services.agent.middleware.sequential_tools import SequentialToolExecutionMiddleware
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

    def _build_summarization_middleware():
        """构建上下文压缩中间件"""
        inner = SummarizationMiddleware(
            model=model,
            trigger=("messages", settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES),
            keep=("messages", settings.AGENT_SUMMARIZATION_KEEP_MESSAGES),
            trim_tokens_to_summarize=settings.AGENT_SUMMARIZATION_TRIM_TOKENS,
        )
        return SummarizationBroadcastMiddleware(inner)

    def _build_strict_mode_middleware():
        """构建严格模式中间件"""
        from app.services.agent.policy import get_policy

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
        # Order 90: 上下文压缩
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

    Args:
        config: Agent 运行时配置
        model: LLM 模型实例

    Returns:
        中间件实例列表（按 order 排序）
    """
    mode = config.mode
    specs = _get_middleware_specs(mode, model)
    middlewares: list[Any] = []

    # 从 Agent 配置获取中间件覆盖
    flags = config.middleware_flags

    # 中间件名称到配置 key 的映射
    FLAG_MAPPING = {
        "MemoryOrchestration": "memory_enabled",
        "TodoList": "todo_enabled",
        "Summarization": "summarization_enabled",
        "ToolRetry": "tool_retry_enabled",
        "ToolCallLimit": "tool_limit_enabled",
        "StrictMode": "strict_mode_enabled",
    }

    for spec in sorted(specs, key=lambda s: s.order):
        # 1. 检查 Agent 配置是否覆盖了启用状态
        override_key = FLAG_MAPPING.get(spec.name)
        if flags and override_key:
            override_value = getattr(flags, override_key, None)
            if override_value is not None:
                if not override_value:
                    continue  # 配置禁用了此中间件
                # 配置启用，继续检查
        elif not spec.is_enabled():
            continue

        result = spec.create()
        if result is None:
            continue

        if isinstance(result, list):
            middlewares.extend(result)
            logger.debug(
                f"✓ {spec.name} (order={spec.order})",
                agent_id=config.agent_id,
                count=len(result),
            )
        else:
            middlewares.append(result)
            logger.debug(
                f"✓ {spec.name} (order={spec.order})",
                agent_id=config.agent_id,
            )

    return middlewares


# 类型提示（避免循环导入）
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig
