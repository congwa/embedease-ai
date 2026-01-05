"""记忆编排中间件

三阶段：
1. Request Start：根据 assistant 设置/用户请求判断是否需记忆检索
2. Params Transform：动态注入记忆上下文到 system prompt
3. After Agent：Agent 完成后异步触发 MemoryProcessor（事实抽取 + 图谱抽取）

改进：
- Phase 3 从 awrap_model_call 移至 aafter_agent 钩子，确保只在整轮 Agent 结束后执行一次
- 记忆抽取前后发送 SSE 事件通知前端
- 记忆抽取使用独立 LLM 调用，不走 Agent 中间件栈，不会污染主响应

用法：
    在 AgentService.get_agent() 的 middleware 列表中添加：
    ```python
    if settings.MEMORY_ORCHESTRATION_ENABLED:
        middlewares.insert(0, MemoryOrchestrationMiddleware())
    ```
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("middleware.memory_orchestration")


@dataclass
class MemoryWriteResult:
    """记忆写入结果"""

    facts_added: int = 0
    entities_created: int = 0
    relations_created: int = 0
    profile_updated_fields: list[str] | None = None
    profile_update_source: str | None = None
    success: bool = True
    error: str | None = None


def _get_context_from_request(request: ModelRequest) -> Any:
    """从 ModelRequest.runtime.context 获取 ChatContext"""
    runtime = getattr(request, "runtime", None)
    return getattr(runtime, "context", None) if runtime is not None else None


def _get_user_id_from_request(request: ModelRequest) -> str | None:
    """从请求中获取 user_id"""
    context = _get_context_from_request(request)
    return getattr(context, "user_id", None)


def _get_last_user_message(request: ModelRequest) -> str | None:
    """获取最后一条用户消息"""
    for msg in reversed(request.messages):
        if isinstance(msg, HumanMessage):
            content = getattr(msg, "content", None)
            return content if isinstance(content, str) else None
    return None


class MemoryOrchestrationMiddleware(AgentMiddleware):
    """记忆编排中间件

    三阶段处理：
    1. awrap_model_call：检索记忆并注入到 system prompt
    2. aafter_agent：Agent 完成后异步触发事实抽取和记忆写入
    3. SSE 通知：记忆抽取开始/完成事件推送给前端

    记忆抽取使用独立 LLM 调用（非流式），不走 Agent 中间件栈，不会污染主响应。

    配置：
    - MEMORY_ENABLED: 总开关
    - MEMORY_STORE_ENABLED: 用户画像开关
    - MEMORY_FACT_ENABLED: 事实记忆开关
    - MEMORY_GRAPH_ENABLED: 图谱记忆开关
    - MEMORY_ORCHESTRATION_ENABLED: 编排中间件开关
    - MEMORY_ASYNC_WRITE: 是否异步写入
    """

    def __init__(
        self,
        enabled: bool | None = None,
        inject_profile: bool = True,
        inject_facts: bool = True,
        inject_graph: bool = True,
        async_write: bool | None = None,
        max_facts: int = 5,
        max_graph_entities: int = 5,
    ):
        """初始化记忆编排中间件

        Args:
            enabled: 是否启用（默认读取配置）
            inject_profile: 是否注入用户画像
            inject_facts: 是否注入事实记忆
            inject_graph: 是否注入图谱记忆
            async_write: 是否异步写入记忆（默认读取配置）
            max_facts: 注入的最大事实数
            max_graph_entities: 注入的最大图谱实体数
        """
        self.enabled = (
            enabled if enabled is not None else settings.MEMORY_ORCHESTRATION_ENABLED
        )
        self.inject_profile = inject_profile
        self.inject_facts = inject_facts
        self.inject_graph = inject_graph
        self.async_write = (
            async_write if async_write is not None else settings.MEMORY_ASYNC_WRITE
        )
        self.max_facts = max_facts
        self.max_graph_entities = max_graph_entities

        logger.debug(
            "MemoryOrchestrationMiddleware 初始化",
            enabled=self.enabled,
            inject_profile=self.inject_profile,
            inject_facts=self.inject_facts,
            inject_graph=self.inject_graph,
            async_write=self.async_write,
        )

    async def _get_memory_context(self, user_id: str, query: str) -> str:
        """获取记忆上下文（用于注入 system prompt）

        Args:
            user_id: 用户 ID
            query: 用户查询

        Returns:
            格式化的记忆上下文字符串
        """
        if not settings.MEMORY_ENABLED:
            return ""

        context_parts = []

        # 1. 用户画像（从 Store）
        if self.inject_profile and settings.MEMORY_STORE_ENABLED:
            try:
                from app.services.memory.store import get_user_profile_store

                store = await get_user_profile_store()
                profile = await store.get_user_profile(user_id)
                if profile:
                    profile_str = self._format_profile(profile)
                    if profile_str:
                        context_parts.append(f"## 用户画像\n{profile_str}")
            except Exception as e:
                logger.warning("获取用户画像失败", error=str(e), user_id=user_id)

        # 2. 相关事实（从 FactMemory）
        if self.inject_facts and settings.MEMORY_FACT_ENABLED:
            try:
                from app.services.memory.fact_memory import get_fact_memory_service

                fact_service = await get_fact_memory_service()
                facts = await fact_service.search_facts(
                    user_id, query, limit=self.max_facts
                )
                if facts:
                    facts_str = "\n".join([f"- {f.content}" for f in facts])
                    context_parts.append(f"## 用户历史记忆\n{facts_str}")
            except Exception as e:
                logger.warning("获取事实记忆失败", error=str(e), user_id=user_id)

        # 3. 相关图谱（从 GraphMemory）
        if self.inject_graph and settings.MEMORY_GRAPH_ENABLED:
            try:
                from app.services.memory.graph_memory import get_graph_manager

                graph_manager = await get_graph_manager()
                # 先搜索与查询相关的节点
                graph = await graph_manager.search_nodes(query)
                if not graph.entities:
                    # 如果没有匹配，尝试获取用户相关的图谱
                    graph = await graph_manager.get_user_graph(user_id)

                if graph.entities:
                    graph_str = self._format_graph(graph)
                    if graph_str:
                        context_parts.append(f"## 知识图谱\n{graph_str}")
            except Exception as e:
                logger.warning("获取图谱记忆失败", error=str(e), user_id=user_id)

        if context_parts:
            return "\n\n".join(context_parts)
        return ""

    def _format_profile(self, profile: dict[str, Any]) -> str:
        """格式化用户画像"""
        parts = []
        if profile.get("nickname"):
            parts.append(f"称谓: {profile['nickname']}")
        if profile.get("tone_preference"):
            parts.append(f"语气偏好: {profile['tone_preference']}")
        if profile.get("budget_min") or profile.get("budget_max"):
            budget_min = profile.get("budget_min", 0)
            budget_max = profile.get("budget_max", "不限")
            parts.append(f"预算范围: ¥{budget_min} - ¥{budget_max}")
        if profile.get("favorite_categories"):
            categories = profile["favorite_categories"]
            if isinstance(categories, list) and categories:
                parts.append(f"偏好品类: {', '.join(categories[:5])}")
        if profile.get("custom_data"):
            custom = profile["custom_data"]
            if isinstance(custom, dict):
                for k, v in list(custom.items())[:3]:
                    parts.append(f"{k}: {v}")
        return "\n".join(parts) if parts else ""

    def _format_graph(self, graph) -> str:
        """格式化图谱"""
        parts = []
        for entity in graph.entities[: self.max_graph_entities]:
            # 过滤掉 user 标记
            obs = [o for o in entity.observations if not o.startswith("[user:")][:3]
            obs_str = ", ".join(obs) if obs else ""
            if obs_str:
                parts.append(f"- {entity.name}({entity.entity_type}): {obs_str}")
            else:
                parts.append(f"- {entity.name}({entity.entity_type})")

        # 添加关系信息
        if graph.relations:
            relation_strs = []
            for r in graph.relations[:5]:
                relation_strs.append(f"{r.from_entity} --[{r.relation_type}]--> {r.to_entity}")
            if relation_strs:
                parts.append("\n关系: " + "; ".join(relation_strs))

        return "\n".join(parts) if parts else ""

    async def _process_memory_write(
        self,
        user_id: str,
        messages: list,
    ) -> MemoryWriteResult:
        """处理记忆写入（事实抽取 + 图谱抽取）

        Args:
            user_id: 用户 ID
            messages: 完整的对话消息列表（包含 HumanMessage 和 AIMessage）

        Returns:
            MemoryWriteResult 包含写入统计
        """
        if not settings.MEMORY_ENABLED:
            return MemoryWriteResult()

        try:
            # 构建对话上下文
            conversation = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    content = getattr(msg, "content", None)
                    if content:
                        conversation.append({"role": "user", "content": str(content)})
                elif isinstance(msg, AIMessage):
                    content = getattr(msg, "content", None)
                    if content:
                        conversation.append({"role": "assistant", "content": str(content)})

            if not conversation:
                return MemoryWriteResult()

            fact_count = 0
            entity_count = 0
            relation_count = 0
            profile_updated_fields: list[str] = []
            profile_update_source: str | None = None
            extracted_facts = []
            extracted_graph = None

            # 事实抽取与写入
            fact_start = time.perf_counter()
            if settings.MEMORY_FACT_ENABLED:
                try:
                    from app.services.memory.fact_memory import get_fact_memory_service

                    fact_service = await get_fact_memory_service()
                    fact_count = await fact_service.process_conversation(
                        user_id, conversation
                    )
                    # 获取最近添加的事实用于画像更新
                    if fact_count > 0:
                        extracted_facts = await fact_service.get_recent_facts(
                            user_id, limit=fact_count
                        )
                except Exception as e:
                    logger.warning("事实记忆写入失败", error=str(e))
            fact_elapsed = int((time.perf_counter() - fact_start) * 1000)
            logger.debug(
                "memory.write.fact_complete",
                user_id=user_id,
                fact_count=fact_count,
                elapsed_ms=fact_elapsed,
            )

            # 图谱抽取与写入
            graph_start = time.perf_counter()
            if settings.MEMORY_GRAPH_ENABLED:
                try:
                    from app.services.memory.graph_memory import get_graph_manager

                    graph_manager = await get_graph_manager()
                    entity_count, relation_count = await graph_manager.extract_and_save(
                        user_id, conversation
                    )
                    # 获取用户图谱用于画像更新
                    if entity_count > 0 or relation_count > 0:
                        extracted_graph = await graph_manager.get_user_graph(user_id)
                except Exception as e:
                    logger.warning("图谱记忆写入失败", error=str(e))
            graph_elapsed = int((time.perf_counter() - graph_start) * 1000)
            logger.debug(
                "memory.write.graph_complete",
                user_id=user_id,
                entity_count=entity_count,
                relation_count=relation_count,
                elapsed_ms=graph_elapsed,
            )

            # 从事实和图谱更新用户画像
            profile_start = time.perf_counter()
            if settings.MEMORY_STORE_ENABLED and (extracted_facts or extracted_graph):
                try:
                    from app.services.memory.profile_service import get_profile_service

                    profile_service = await get_profile_service()

                    # 从事实更新画像
                    if extracted_facts:
                        fact_result = await profile_service.update_from_facts(
                            user_id, extracted_facts
                        )
                        if fact_result.updated_fields:
                            profile_updated_fields.extend(fact_result.updated_fields)
                            profile_update_source = "fact"

                    # 从图谱更新画像
                    if extracted_graph and (
                        extracted_graph.entities or extracted_graph.relations
                    ):
                        graph_result = await profile_service.update_from_graph(
                            user_id, extracted_graph
                        )
                        if graph_result.updated_fields:
                            profile_updated_fields.extend(graph_result.updated_fields)
                            if not profile_update_source:
                                profile_update_source = "graph"
                            else:
                                profile_update_source = "fact+graph"

                    if profile_updated_fields:
                        logger.info(
                            "用户画像更新",
                            user_id=user_id,
                            updated_fields=profile_updated_fields,
                            source=profile_update_source,
                        )
                except Exception as e:
                    logger.warning("画像更新失败", error=str(e), user_id=user_id)
            profile_elapsed = int((time.perf_counter() - profile_start) * 1000)
            logger.debug(
                "memory.write.profile_complete",
                user_id=user_id,
                updated_fields=profile_updated_fields,
                elapsed_ms=profile_elapsed,
            )

            if fact_count > 0 or entity_count > 0 or profile_updated_fields:
                logger.info(
                    "记忆写入完成",
                    user_id=user_id,
                    facts=fact_count,
                    entities=entity_count,
                    relations=relation_count,
                    profile_fields=len(profile_updated_fields),
                )

            return MemoryWriteResult(
                facts_added=fact_count,
                entities_created=entity_count,
                relations_created=relation_count,
                profile_updated_fields=profile_updated_fields if profile_updated_fields else None,
                profile_update_source=profile_update_source,
                success=True,
            )

        except Exception as e:
            logger.error("记忆写入失败", error=str(e), user_id=user_id)
            return MemoryWriteResult(success=False, error=str(e))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """包装模型调用

        Args:
            request: 模型请求
            handler: 下游处理器

        Returns:
            模型响应
        """
        # 如果禁用，直接透传
        if not self.enabled or not settings.MEMORY_ENABLED:
            return await handler(request)

        user_id = _get_user_id_from_request(request)
        user_query = _get_last_user_message(request)

        # === Phase 1 & 2: Request Start + Params Transform ===
        # 注入记忆上下文到 system prompt
        if user_id and user_query:
            try:
                memory_context = await self._get_memory_context(user_id, user_query)
                if memory_context:
                    # 在 system message 后追加记忆上下文
                    if request.system_message:
                        original_content = request.system_message.content
                        enhanced_content = (
                            f"{original_content}\n\n---\n"
                            f"# 记忆上下文（基于用户历史）\n{memory_context}"
                        )
                        # 创建新的 SystemMessage（ModelRequest 可能是不可变的）
                        request = ModelRequest(
                            model=request.model,
                            messages=request.messages,
                            system_message=SystemMessage(content=enhanced_content),
                            tools=request.tools,
                            tool_choice=request.tool_choice,
                            response_format=request.response_format,
                            model_settings=request.model_settings,
                            runtime=request.runtime,
                        )
                    logger.debug(
                        "已注入记忆上下文",
                        user_id=user_id,
                        context_len=len(memory_context),
                    )
            except Exception as e:
                logger.warning("注入记忆上下文失败", error=str(e), user_id=user_id)

        # 调用模型（Phase 3 已移至 aafter_agent 钩子）
        return await handler(request)

    async def aafter_agent(
        self,
        state: AgentState,
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """Agent 完成后触发记忆写入

        在整轮 Agent 结束后执行一次，确保：
        1. 记忆写入不会在每次模型调用时重复执行
        2. 记忆抽取的 LLM 调用不会污染主响应流
        3. 通过 SSE 通知前端记忆抽取进度

        Args:
            state: Agent 最终状态（包含完整对话历史）
            runtime: 运行时上下文

        Returns:
            None（不修改 state）
        """
        if not self.enabled or not settings.MEMORY_ENABLED:
            return None

        # 从 runtime.context 获取上下文信息
        context = getattr(runtime, "context", None)
        if context is None:
            return None

        user_id = getattr(context, "user_id", None)
        conversation_id = getattr(context, "conversation_id", None)
        emitter = getattr(context, "emitter", None)

        if not user_id:
            return None

        # 获取对话消息
        messages = state.get("messages", [])
        if not messages:
            return None

        logger.debug(
            "after_agent: 准备触发记忆写入",
            user_id=user_id,
            conversation_id=conversation_id,
            message_count=len(messages),
        )

        # 定义带 SSE 通知的记忆写入包装器
        async def _memory_write_with_sse() -> None:
            start_time = time.time()

            # 发送记忆抽取开始事件
            if emitter and hasattr(emitter, "aemit"):
                try:
                    await emitter.aemit(
                        StreamEventType.MEMORY_EXTRACTION_START.value,
                        {
                            "conversation_id": conversation_id or "",
                            "user_id": user_id,
                        },
                    )
                except Exception as e:
                    logger.warning("发送记忆抽取开始事件失败", error=str(e))

            # 执行记忆写入
            result = await self._process_memory_write(user_id, list(messages))

            elapsed_ms = int((time.time() - start_time) * 1000)

            # 发送记忆抽取完成事件
            if emitter and hasattr(emitter, "aemit"):
                try:
                    await emitter.aemit(
                        StreamEventType.MEMORY_EXTRACTION_COMPLETE.value,
                        {
                            "conversation_id": conversation_id or "",
                            "user_id": user_id,
                            "facts_added": result.facts_added,
                            "entities_created": result.entities_created,
                            "relations_created": result.relations_created,
                            "duration_ms": elapsed_ms,
                            "status": "success" if result.success else "failed",
                            "error": result.error,
                        },
                    )
                except Exception as e:
                    logger.warning("发送记忆抽取完成事件失败", error=str(e))

                # 发送画像更新事件
                if result.profile_updated_fields:
                    try:
                        await emitter.aemit(
                            StreamEventType.MEMORY_PROFILE_UPDATED.value,
                            {
                                "user_id": user_id,
                                "updated_fields": result.profile_updated_fields,
                                "source": result.profile_update_source,
                            },
                        )
                    except Exception as e:
                        logger.warning("发送画像更新事件失败", error=str(e))

        # 根据配置决定异步或同步执行
        if self.async_write:
            asyncio.create_task(_memory_write_with_sse())
        else:
            await _memory_write_with_sse()

        return None
