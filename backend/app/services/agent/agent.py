"""LangChain v1.1 Agent 服务"""

import asyncio
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import aiosqlite
from langchain.agents import create_agent
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware.todo import TodoListMiddleware
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain.agents.middleware.tool_retry import ToolRetryMiddleware
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.database import get_db_context
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.services.catalog_profile import CatalogProfileService
from app.services.agent.tools import (
    search_products,
    get_product_details,
    compare_products,
    filter_by_price,
    guide_user,
    list_all_categories,
    get_category_overview,
    list_products_by_category,
    find_similar_products,
    list_featured_products,
    list_products_by_attribute,
    suggest_related_categories,
    get_product_purchase_links,
)
from app.services.agent.middleware.logging import LoggingMiddleware
from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware
from app.services.agent.middleware.llm_call_sse import SSEMiddleware
from app.services.agent.middleware.sequential_tools import SequentialToolExecutionMiddleware
from app.services.agent.middleware.strict_mode import StrictModeMiddleware
from app.services.agent.middleware.summarization_broadcast import SummarizationBroadcastMiddleware
from app.services.agent.middleware.todo_broadcast import TodoBroadcastMiddleware
from app.services.memory.middleware.orchestration import MemoryOrchestrationMiddleware
from app.services.streaming.context import ChatContext
from app.schemas.events import StreamEventType
from app.schemas.recommendation import RecommendationResult

logger = get_logger("agent")


# ========== 中间件配置（声明式，顺序即执行顺序） ==========

@dataclass
class MiddlewareSpec:
    """中间件规格定义
    
    Attributes:
        name: 中间件名称（用于日志）
        enabled: 是否启用（可以是 bool 或返回 bool 的 callable）
        factory: 中间件工厂函数，返回中间件实例或 None
        order: 执行顺序（数字越小越先执行）
    """
    name: str
    enabled: bool | Callable[[], bool]
    factory: Callable[[], Any | None]
    order: int = 100

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

# ========== 聊天模式对应的 System Prompt ==========

NATURAL_SYSTEM_PROMPT = """你是一个专业的商品推荐助手，帮助用户发现和选择合适的商品。

## 核心原则
- 理解用户的购物需求和偏好，提供个性化的商品推荐
- 只推荐基于真实数据的商品，不编造信息
- 突出商品的核心卖点和性价比
- 保持友好、专业的语气

## 输出格式
当推荐商品时，请使用以下格式：

根据您的需求，我为您推荐以下商品：

### 1. **商品名称** - ¥价格
**推荐理由**：...
**适合人群**：...

### 2. **商品名称** - ¥价格
**推荐理由**：...
**适合人群**：...

如果用户询问非商品相关的问题，礼貌地引导他们回到商品推荐话题。
"""

FREE_SYSTEM_PROMPT = """你是一个友好的智能助手，可以与用户自由交流各种话题。

## 核心原则
- 可以回答各类问题（知识、建议、闲聊等）
- 当用户有购物需求时，可以帮助检索和推荐商品
- 保持自然、友好的对话风格
- 不要强行引导用户回到商品话题
- 推荐商品时，只推荐基于真实数据的商品，不编造信息
"""

STRICT_SYSTEM_PROMPT = """你是一个专业的商品推荐助手，致力于为用户提供准确、有据可依的商品建议。

## 核心原则
- **数据驱动**：所有推荐和建议必须基于真实数据
- **准确可靠**：推荐商品时必须引用具体数据（名称、价格、特点等）
- **诚实透明**：如果没有找到合适的商品或信息不足，请如实告知并引导用户补充
- **不编造信息**：只推荐基于检索结果的真实商品

## 输出要求
- 推荐商品时必须引用具体数据
- 保持客观中立，基于数据给出建议
"""

STRICT_MODE_FALLBACK_MESSAGE = """**严格模式提示**

我需要先通过工具获取真实数据才能回答您的问题。

当前这轮对话我没有获取到可引用的工具输出，因此无法给出可靠的推荐。

您可以：
1. **补充关键信息**：告诉我您的预算范围、品类偏好、使用场景等
2. **让我先检索**：我会调用工具获取商品数据后再回答
3. **切换模式**：如果您只是想随便聊聊，可以切换到自由聊天模式
"""

# 兼容旧代码
SYSTEM_PROMPT = NATURAL_SYSTEM_PROMPT


def _normalize_products_payload(payload: Any) -> list[dict[str, Any]] | None:
    if payload is None:
        return None

    candidate: Any = payload
    if isinstance(candidate, dict) and "products" in candidate and isinstance(candidate.get("products"), list):
        candidate = candidate.get("products")

    if not isinstance(candidate, list):
        return None

    normalized: list[dict[str, Any]] = []
    for item in candidate:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if raw_id is None:
            continue
        normalized_item = dict(item)
        normalized_item["id"] = str(raw_id)
        normalized.append(normalized_item)

    return normalized or None


class AgentService:
    """Agent 服务 - 管理 LangChain Agent 的生命周期"""

    _instance: "AgentService | None" = None
    _agents: dict[str, CompiledStateGraph]  # 按 mode 缓存不同的 agent
    _checkpointer: AsyncSqliteSaver | None = None
    _conn: aiosqlite.Connection | None = None
    _checkpoint_path: str | None = None
    
    # 商品库画像缓存（TTL + fingerprint 变化检测）
    _catalog_profile_prompt: str | None = None
    _catalog_profile_fingerprint: str | None = None
    _catalog_profile_cached_at: float | None = None
    _catalog_profile_lock: asyncio.Lock | None = None

    def __new__(cls) -> "AgentService":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            # 初始化画像缓存字段
            cls._instance._catalog_profile_prompt = None
            cls._instance._catalog_profile_fingerprint = None
            cls._instance._catalog_profile_cached_at = None
            cls._instance._catalog_profile_lock = asyncio.Lock()
        return cls._instance

    async def _get_checkpointer(self) -> AsyncSqliteSaver:
        """获取 checkpointer"""
        # 如果 checkpointer 已存在且连接有效，直接返回
        if self._checkpointer is not None and self._conn is not None:
            # 检查连接是否仍然有效
            try:
                # 尝试执行一个简单的查询来验证连接
                await self._conn.execute("SELECT 1")
                return self._checkpointer
            except Exception:
                # 连接已失效，需要重新创建
                self._checkpointer = None
                if self._conn:
                    try:
                        await self._conn.close()
                    except Exception:
                        pass
                self._conn = None

        # 创建新的 checkpointer
        settings.ensure_data_dir()
        self._checkpoint_path = settings.CHECKPOINT_DB_PATH

        self._conn = await aiosqlite.connect(
            self._checkpoint_path,
            isolation_level=None,  # 自动提交模式，避免连接问题
        )

        # 添加 is_alive 方法以兼容 AsyncSqliteSaver 的检查
        # AsyncSqliteSaver.setup() 会调用 conn.is_alive() 来检查连接状态
        # aiosqlite.Connection 默认没有这个方法，我们需要手动添加
        try:
            if not hasattr(self._conn, "is_alive"):
                # 创建一个简单的方法来检查连接是否有效
                # 对于 aiosqlite.Connection，连接对象存在就表示有效
                # 如果连接无效，后续操作会抛出异常
                # 注意：当绑定为方法时，第一个参数是连接对象本身
                def is_alive(conn) -> bool:  # noqa: ARG001
                    """检查连接是否仍然有效"""
                    return True  # aiosqlite 连接对象存在即表示有效

                # 将 is_alive 设置为方法
                import types

                bound_method = types.MethodType(is_alive, self._conn)
                setattr(self._conn, "is_alive", bound_method)
        except (AttributeError, TypeError):
            pass

        self._checkpointer = AsyncSqliteSaver(self._conn)
        await self._checkpointer.setup()

        return self._checkpointer

    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            try:
                await self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None
                self._checkpointer = None
                self._agents = {}

    def _get_system_prompt(self, mode: str) -> str:
        """根据模式获取对应的 system prompt"""
        if mode == "free":
            return FREE_SYSTEM_PROMPT
        elif mode == "strict":
            return STRICT_SYSTEM_PROMPT
        else:
            return NATURAL_SYSTEM_PROMPT

    def _invalidate_all_agents(self) -> None:
        """清空所有 mode 的 agent 缓存（画像变化时触发重建）"""
        if self._agents:
            logger.info("画像变化，清空所有 agent 缓存以触发重建", agent_count=len(self._agents))
        self._agents = {}

    async def _get_catalog_profile_prompt(self) -> str:
        """获取商品库画像提示词（带 TTL 缓存 + fingerprint 变化检测）
        
        流程：
        1. 若功能关闭，返回空
        2. 若缓存命中且 TTL 未过期，直接返回
        3. 否则从 DB 读取画像，若 fingerprint 变化则清空 agents
        
        Returns:
            画像提示词（<=100 字），或空字符串
        """
        # 1. 功能开关
        if not settings.CATALOG_PROFILE_ENABLED:
            return ""
        
        # 2. 快路径：缓存命中且 TTL 未过期
        now = time.monotonic()
        ttl = settings.CATALOG_PROFILE_TTL_SECONDS
        if (
            self._catalog_profile_prompt is not None
            and self._catalog_profile_cached_at is not None
            and (now - self._catalog_profile_cached_at) < ttl
        ):
            return self._catalog_profile_prompt
        
        # 3. 慢路径：加锁读取 DB
        async with self._catalog_profile_lock:
            # 双重检查（避免并发重复读取）
            if (
                self._catalog_profile_prompt is not None
                and self._catalog_profile_cached_at is not None
                and (time.monotonic() - self._catalog_profile_cached_at) < ttl
            ):
                return self._catalog_profile_prompt
            
            try:
                async with get_db_context() as session:
                    service = CatalogProfileService(session)
                    prompt, fingerprint = await service.get_prompt_and_fingerprint()
                
                # 检测 fingerprint 变化
                old_fp = self._catalog_profile_fingerprint
                if old_fp is not None and fingerprint and fingerprint != old_fp:
                    self._invalidate_all_agents()
                
                # 更新缓存
                self._catalog_profile_prompt = prompt
                self._catalog_profile_fingerprint = fingerprint
                self._catalog_profile_cached_at = time.monotonic()
                
                if prompt:
                    logger.debug(
                        "加载商品库画像",
                        prompt_len=len(prompt),
                        fingerprint_prefix=fingerprint[:8] if fingerprint else None,
                    )
                
                return prompt
            
            except Exception as e:
                # 读取失败不阻塞业务，返回空字符串
                logger.warning("加载商品库画像失败", error=str(e))
                return self._catalog_profile_prompt or ""

    async def get_agent(
        self,
        mode: str = "natural",
        use_structured_output: bool = False,
    ) -> CompiledStateGraph:
        """获取 Agent 实例

        Args:
            mode: 聊天模式（natural/free/strict）
            use_structured_output: 是否使用结构化输出

        Returns:
            编译后的 Agent 图
        """
        if mode not in self._agents:
            # 初始化模型
            model = get_chat_model()

            # 初始化 checkpointer
            checkpointer = await self._get_checkpointer()

            # 准备工具列表
            tools = [
                search_products,
                get_product_details,
                compare_products,
                filter_by_price,
                guide_user,
                list_all_categories,
                get_category_overview,
                list_products_by_category,
                find_similar_products,
                list_featured_products,
                list_products_by_attribute,
                suggest_related_categories,
                get_product_purchase_links,
            ]

            # ========== 中间件链配置（声明式，顺序一目了然） ==========
            # 
            # 📋 中间件执行顺序（按 order 从小到大排列）:
            # ┌─────┬──────────────────────────────────┬────────────────────────────┐
            # │Order│ 中间件名称                        │ 说明                        │
            # ├─────┼──────────────────────────────────┼────────────────────────────┤
            # │  10 │ MemoryOrchestration              │ 记忆注入 + 异步写入          │
            # │  20 │ ResponseSanitization             │ 响应内容安全过滤             │
            # │  30 │ SSE                              │ LLM 调用事件推送             │
            # │  40 │ TodoList + TodoBroadcast         │ 任务规划 + 广播              │
            # │  50 │ SequentialToolExecution          │ 工具串行执行                 │
            # │  60 │ Logging                          │ 日志记录                    │
            # │  70 │ ToolRetry                        │ 工具重试                    │
            # │  80 │ ToolCallLimit                    │ 工具调用限制                 │
            # │  90 │ Summarization                    │ 上下文压缩                  │
            # │ 100 │ StrictMode                       │ 严格模式检查                 │
            # └─────┴──────────────────────────────────┴────────────────────────────┘

            def _build_tool_limit_middleware():
                """构建工具调用限制中间件"""
                limit_kwargs = {"exit_behavior": settings.AGENT_TOOL_LIMIT_EXIT_BEHAVIOR}
                if settings.AGENT_TOOL_LIMIT_THREAD is not None:
                    limit_kwargs["thread_limit"] = settings.AGENT_TOOL_LIMIT_THREAD
                if settings.AGENT_TOOL_LIMIT_RUN is not None:
                    limit_kwargs["run_limit"] = settings.AGENT_TOOL_LIMIT_RUN
                if "thread_limit" not in limit_kwargs and "run_limit" not in limit_kwargs:
                    return None
                return ToolCallLimitMiddleware(**limit_kwargs)

            def _build_todo_middlewares():
                """构建 TODO 中间件列表"""
                todo_kwargs = {}
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

            # 中间件规格列表（按 order 排序后依次构建）
            middleware_specs: list[MiddlewareSpec] = [
                # Order 10: 记忆编排（最先执行，注入记忆上下文）
                MiddlewareSpec(
                    name="MemoryOrchestration",
                    enabled=settings.MEMORY_ENABLED and settings.MEMORY_ORCHESTRATION_ENABLED,
                    factory=MemoryOrchestrationMiddleware,
                    order=10,
                ),
                # Order 20: 响应安全过滤
                MiddlewareSpec(
                    name="ResponseSanitization",
                    enabled=True,
                    factory=lambda: ResponseSanitizationMiddleware(
                        enabled=settings.RESPONSE_SANITIZATION_ENABLED,
                        custom_fallback_message=settings.RESPONSE_SANITIZATION_CUSTOM_MESSAGE,
                    ),
                    order=20,
                ),
                # Order 30: SSE 事件推送（llm.call.start/end）
                MiddlewareSpec(
                    name="SSE",
                    enabled=True,
                    factory=SSEMiddleware,
                    order=30,
                ),
                # Order 40: TODO 任务规划 + 广播
                MiddlewareSpec(
                    name="TodoList",
                    enabled=settings.AGENT_TODO_ENABLED,
                    factory=_build_todo_middlewares,
                    order=40,
                ),
                # Order 50: 工具串行执行
                MiddlewareSpec(
                    name="SequentialToolExecution",
                    enabled=settings.AGENT_SERIALIZE_TOOLS,
                    factory=SequentialToolExecutionMiddleware,
                    order=50,
                ),
                # Order 60: 日志记录
                MiddlewareSpec(
                    name="Logging",
                    enabled=True,
                    factory=LoggingMiddleware,
                    order=60,
                ),
                # Order 70: 工具重试
                MiddlewareSpec(
                    name="ToolRetry",
                    enabled=settings.AGENT_TOOL_RETRY_ENABLED,
                    factory=lambda: ToolRetryMiddleware(
                        max_retries=settings.AGENT_TOOL_RETRY_MAX_RETRIES,
                        backoff_factor=settings.AGENT_TOOL_RETRY_BACKOFF_FACTOR,
                        initial_delay=settings.AGENT_TOOL_RETRY_INITIAL_DELAY,
                        max_delay=settings.AGENT_TOOL_RETRY_MAX_DELAY,
                    ),
                    order=70,
                ),
                # Order 80: 工具调用限制
                MiddlewareSpec(
                    name="ToolCallLimit",
                    enabled=settings.AGENT_TOOL_LIMIT_ENABLED,
                    factory=_build_tool_limit_middleware,
                    order=80,
                ),
                # Order 90: 上下文压缩
                MiddlewareSpec(
                    name="Summarization",
                    enabled=settings.AGENT_SUMMARIZATION_ENABLED,
                    factory=_build_summarization_middleware,
                    order=90,
                ),
                # Order 100: 严格模式检查（最后执行）
                MiddlewareSpec(
                    name="StrictMode",
                    enabled=mode == "strict",
                    factory=_build_strict_mode_middleware,
                    order=100,
                ),
            ]

            # 按 order 排序并构建中间件列表
            middlewares = []
            for spec in sorted(middleware_specs, key=lambda s: s.order):
                if not spec.is_enabled():
                    continue
                result = spec.create()
                if result is None:
                    continue
                # 支持返回列表（如 TodoList 返回 [TodoListMiddleware, TodoBroadcastMiddleware]）
                if isinstance(result, list):
                    middlewares.extend(result)
                    logger.debug(f"启用 {spec.name} 中间件", count=len(result))
                else:
                    middlewares.append(result)
                    logger.debug(f"启用 {spec.name} 中间件")

            # 获取对应模式的 system prompt
            base_prompt = self._get_system_prompt(mode)
            
            # 拼接商品库画像提示词（如果启用）
            catalog_prompt = await self._get_catalog_profile_prompt()
            if catalog_prompt.strip():
                system_prompt = base_prompt + "\n\n" + catalog_prompt
            else:
                system_prompt = base_prompt

            # 创建 Agent
            try:
                agent_kwargs = {
                    "model": model,
                    "tools": tools,
                    "system_prompt": system_prompt,
                    "checkpointer": checkpointer,
                    "middleware": middlewares,
                    # 启用 LangGraph 标准 context 注入：invoke/stream 时传入的 context 会被注入到 Runtime.context，
                    # ToolNode 会进一步注入到 ToolRuntime.context，供 tools/middleware 使用。
                    "context_schema": ChatContext,
                }

                # 可选：使用结构化输出
                if use_structured_output:
                    agent_kwargs["response_format"] = RecommendationResult

                self._agents[mode] = create_agent(**agent_kwargs)
                logger.info(
                    "创建 Agent 实例",
                    mode=mode,
                    system_prompt_preview=system_prompt[:100] + "...",
                )

            except TypeError:
                # 兼容较老版本：不支持某些参数时回退
                self._agents[mode] = create_agent(
                    model=model,
                    tools=tools,
                    system_prompt=system_prompt,
                    checkpointer=checkpointer,
                )

        return self._agents[mode]

    async def chat_emit(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str,
        context: ChatContext,
    ) -> None:
        """将聊天流事件写入 context.emitter（不绕过 Orchestrator）。

        说明：
        - 这里不直接返回/写 SSE，只发 domain events（type + payload）
        - Orchestrator 作为唯一对外 SSE 出口
        
        推理内容提取（多态架构）：
        - 通过 model.extract_reasoning(msg) 获取统一的 ReasoningChunk
        - 不同平台在各自的实现中完成推理字段提取
        - 新增平台无需修改本文件
        """
        mode = getattr(context, "mode", "natural")
        agent = await self.get_agent(mode=mode)
        
        # 获取模型实例（用于多态的推理提取）
        model = get_chat_model()

        emitter = getattr(context, "emitter", None)
        if emitter is None or not hasattr(emitter, "aemit"):
            raise RuntimeError("chat_emit 需要 context.emitter.aemit()（用于高频不丢事件）")

        full_content = ""
        full_reasoning = ""
        products_data: Any | None = None
        seen_tool_message_ids: set[str] = set()

        # 准备 Agent 输入
        agent_input = {"messages": [HumanMessage(content=message)]}
        agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}

        # 统计/观测：用于 debug 数据流（不影响业务）
        reasoning_char_count = 0
        reasoning_event_count = 0
        content_event_count = 0

        try:
            # 关键：使用 LangGraph 的 messages 模式拿到 AIMessageChunk（而不是 state values）
            async for item in agent.astream(
                agent_input,
                config=agent_config,
                context=context,
                stream_mode="messages",
            ):
                # 兼容不同版本：可能返回 msg 或 (msg, meta)
                msg = item[0] if isinstance(item, (tuple, list)) and item else item

                # 1) 模型 chunk：正文按 chunk 推送；推理按统一接口提取
                if isinstance(msg, AIMessageChunk):
                    # 正文增量
                    delta = msg.content or ""
                    if isinstance(delta, list):
                        delta = "".join(str(x) for x in delta)
                    if isinstance(delta, str) and delta:
                        full_content += delta
                        content_event_count += 1
                        await emitter.aemit(
                            StreamEventType.ASSISTANT_DELTA.value,
                            {"delta": delta},
                        )

                    # 推理增量（通过多态接口提取，不依赖 additional_kwargs）
                    reasoning_chunk = None
                    if hasattr(model, "extract_reasoning"):
                        reasoning_chunk = model.extract_reasoning(msg)
                    
                    if reasoning_chunk and reasoning_chunk.delta:
                        full_reasoning += reasoning_chunk.delta
                        reasoning_char_count += len(reasoning_chunk.delta)
                        reasoning_event_count += 1
                        await emitter.aemit(
                            StreamEventType.ASSISTANT_REASONING_DELTA.value,
                            {"delta": reasoning_chunk.delta},
                        )

                # 1.1) 部分模型/版本会在流末尾给出完整 AIMessage（非 chunk）
                # 这种情况下 content 可能为空，需要兜底吸收。
                elif isinstance(msg, AIMessage):
                    if content_event_count == 0:
                        delta = msg.content or ""
                        if isinstance(delta, list):
                            delta = "".join(str(x) for x in delta)
                        if isinstance(delta, str) and delta:
                            full_content += delta
                            content_event_count += 1
                            await emitter.aemit(
                                StreamEventType.ASSISTANT_DELTA.value,
                                {"delta": delta},
                            )

                    # 兜底：从完整 AIMessage 提取推理（如果之前没有收到任何推理增量）
                    if reasoning_event_count == 0 and hasattr(model, "extract_reasoning"):
                        reasoning_chunk = model.extract_reasoning(msg)
                        if reasoning_chunk and reasoning_chunk.delta:
                            full_reasoning += reasoning_chunk.delta
                            reasoning_char_count += len(reasoning_chunk.delta)
                            reasoning_event_count += 1
                            await emitter.aemit(
                                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                                {"delta": reasoning_chunk.delta},
                            )

                # 2) 工具消息：解析 products
                elif isinstance(msg, ToolMessage):
                    msg_id = getattr(msg, "id", None)
                    if isinstance(msg_id, str) and msg_id in seen_tool_message_ids:
                        continue
                    if isinstance(msg_id, str):
                        seen_tool_message_ids.add(msg_id)

                    content = msg.content
                    try:
                        parsed_products_data: Any
                        if isinstance(content, str):
                            parsed_products_data = json.loads(content)
                        elif isinstance(content, (list, dict)):
                            parsed_products_data = content
                        else:
                            continue

                        normalized_products = _normalize_products_payload(parsed_products_data)
                        if normalized_products is None:
                            continue

                        products_data = normalized_products
                        await emitter.aemit(
                            StreamEventType.ASSISTANT_PRODUCTS.value,
                            {"items": normalized_products},
                        )
                    except Exception:
                        continue

            # 发送完成事件（final 用于 Orchestrator 聚合 + 落库对齐）
            # 兜底：仅当"全程没有任何 content delta"时，才把 reasoning 兜底成 content（避免混流）
            if content_event_count == 0 and full_reasoning.strip():
                logger.warning(
                    "检测到 content 全程为空，兜底将 reasoning 作为 content 输出",
                    conversation_id=conversation_id,
                    content_len=len(full_content),
                    reasoning_len=len(full_reasoning),
                )
                full_content = full_reasoning
                full_reasoning = ""

            await emitter.aemit(
                StreamEventType.ASSISTANT_FINAL.value,
                {
                    "content": full_content,
                    "reasoning": full_reasoning if full_reasoning else None,
                    "products": products_data
                    if isinstance(products_data, list) or products_data is None
                    else [products_data],
                },
            )

            logger.info(
                "✅ chat_emit 完成",
                conversation_id=conversation_id,
                content_events=content_event_count,
                reasoning_events=reasoning_event_count,
                reasoning_chars=reasoning_char_count,
            )

            # 发送最终的 todos（确保前端能接收到 todo 列表更新）
            try:
                final_state = await agent.aget_state(config={"configurable": {"thread_id": conversation_id}})
                todos = final_state.values.get("todos")
                if todos:
                    await emitter.aemit(StreamEventType.ASSISTANT_TODOS.value, {"todos": todos})
                    logger.debug("发送最终 todos", todo_count=len(todos))
            except Exception as e:
                logger.warning("发送最终 todos 失败", error=str(e))

        except Exception as e:
            logger.exception("❌ chat_emit 失败", error=str(e), conversation_id=conversation_id)
            # 将错误也走同一事件通道，确保前端能收到
            try:
                await emitter.aemit(StreamEventType.ERROR.value, {"message": str(e)})
            except Exception:
                pass
        finally:
            # Orchestrator 以 __end__ 作为停止读取信号
            try:
                await emitter.aemit("__end__", None)
            except Exception:
                pass

    async def get_history(self, conversation_id: str) -> list[dict[str, Any]]:
        """获取会话历史"""
        agent = await self.get_agent()

        try:
            state = await agent.aget_state(config={"configurable": {"thread_id": conversation_id}})

            messages = state.values.get("messages", [])
            history = []

            for msg in messages:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    history.append({"role": "assistant", "content": msg.content})

            return history
        except Exception as e:
            logger.error("获取历史失败", error=str(e))
            return []


# 全局单例
agent_service = AgentService()
