"""Agent 服务 - 多 Agent 架构核心

职责：
    - Agent 生命周期管理（创建、缓存、销毁）
    - 基于 (agent_id, mode) 缓存 Agent 实例
    - Checkpointer 管理
    - 聊天流程编排

依赖模块：
    - config.py: AgentConfig 加载器
    - factory.py: Agent 工厂
    - tools/registry.py: 工具注册表
    - middleware/registry.py: 中间件注册表
    - streams/response_handler.py: 流响应处理器
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db_context
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.models.agent import Agent
from app.schemas.agent import AgentConfig
from app.schemas.events import StreamEventType
from app.services.agent.core.config import AgentConfigLoader, get_or_create_default_agent
from app.services.agent.core.factory import build_agent
from app.services.agent.streams import StreamingResponseHandler
from app.services.streaming.context import ChatContext

logger = get_logger("agent.service")


@dataclass
class CachedConfig:
    """带元数据的缓存配置项"""

    config: AgentConfig
    cached_at: float  # 缓存时间戳
    version: str  # 配置版本（用于校验）


class AgentService:
    """Agent 服务 - 管理多 Agent 的生命周期

    缓存键：(agent_id, mode)
    """

    _instance: "AgentService | None" = None
    _agents: dict[tuple[str, str], CompiledStateGraph]  # (agent_id, mode) -> agent
    _agent_configs: dict[tuple[str, str], CachedConfig]  # (agent_id, mode) -> cached config
    _checkpointer: BaseCheckpointSaver | None = None
    _default_agent_id: str | None = None
    _init_lock: asyncio.Lock | None = None

    def __new__(cls) -> "AgentService":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
            cls._instance._agent_configs = {}
            cls._instance._init_lock = asyncio.Lock()
        return cls._instance

    async def _get_checkpointer(self) -> BaseCheckpointSaver:
        """获取 checkpointer（使用统一的 Checkpointer 工厂）"""
        if self._checkpointer is not None:
            return self._checkpointer

        from app.core.db.checkpointer import get_checkpointer

        self._checkpointer = await get_checkpointer()
        return self._checkpointer

    async def close(self) -> None:
        """关闭连接"""
        from app.core.db.checkpointer import close_checkpointer

        try:
            await close_checkpointer()
        except Exception:
            pass
        finally:
            self._checkpointer = None
            self._agents = {}
            self._agent_configs = {}

    async def get_default_agent_id(self) -> str:
        """获取默认 Agent ID"""
        if self._default_agent_id:
            return self._default_agent_id

        async with self._init_lock:
            if self._default_agent_id:
                return self._default_agent_id

            async with get_db_context() as session:
                self._default_agent_id = await get_or_create_default_agent(session)
                await session.commit()

            logger.info("初始化默认 Agent", agent_id=self._default_agent_id)
            return self._default_agent_id

    async def get_agent_config(
        self,
        agent_id: str | None = None,
    ) -> AgentConfig:
        """获取 Agent 配置

        Args:
            agent_id: Agent ID，为空时使用默认 Agent

        Returns:
            Agent 运行时配置
        """
        if agent_id is None:
            agent_id = await self.get_default_agent_id()

        cache_key = agent_id
        now = time.time()
        ttl = settings.AGENT_CACHE_TTL_SECONDS

        # 检查缓存
        if cache_key in self._agent_configs:
            cached = self._agent_configs[cache_key]

            # TTL 为 0 或未过期，直接返回
            if ttl <= 0 or (now - cached.cached_at < ttl):
                return cached.config

            # TTL 过期，校验版本
            current_version = await self._get_config_version(agent_id)
            if current_version == cached.version:
                # 版本未变，刷新 TTL
                self._agent_configs[cache_key] = CachedConfig(
                    config=cached.config,
                    cached_at=now,
                    version=cached.version,
                )
                return cached.config

            # 版本已变，清除缓存
            logger.info(
                "配置版本已变更，清除缓存",
                agent_id=agent_id,
                old_version=cached.version,
                new_version=current_version,
            )
            self._agent_configs.pop(cache_key, None)
            self._agents.pop(cache_key, None)

        # 从数据库加载
        async with get_db_context() as session:
            loader = AgentConfigLoader(session)
            config = await loader.load_config(agent_id)

        if config is None:
            raise ValueError(f"Agent 不存在或已禁用: {agent_id}")

        # 缓存配置（带版本和时间戳）
        self._agent_configs[cache_key] = CachedConfig(
            config=config,
            cached_at=now,
            version=config.config_version,
        )
        return config

    async def _get_config_version(self, agent_id: str) -> str:
        """轻量级版本查询（仅查 updated_at，避免全量加载）

        Args:
            agent_id: Agent ID

        Returns:
            版本字符串（基于 updated_at 时间戳）
        """
        async with get_db_context() as session:
            stmt = select(Agent.updated_at).where(Agent.id == agent_id)
            result = await session.execute(stmt)
            row = result.first()
            if not row or row[0] is None:
                return ""
            return str(row[0].timestamp())

    async def get_agent(
        self,
        agent_id: str | None = None,
        use_structured_output: bool = False,
    ) -> CompiledStateGraph:
        """获取 Agent 实例

        Args:
            agent_id: Agent ID，为空时使用默认 Agent
            use_structured_output: 是否使用结构化输出

        Returns:
            编译后的 Agent 图
        """
        if agent_id is None:
            agent_id = await self.get_default_agent_id()

        cache_key = agent_id

        if cache_key not in self._agents:
            # 加载配置
            config = await self.get_agent_config(agent_id)

            # 获取 checkpointer
            checkpointer = await self._get_checkpointer()

            # 构建 Agent（使用数据库 session 获取 LLM 配置）
            async with get_db_context() as session:
                agent = await build_agent(
                    config=config,
                    checkpointer=checkpointer,
                    use_structured_output=use_structured_output,
                    session=session,
                )

            self._agents[cache_key] = agent
            logger.info(
                "创建 Agent 实例",
                agent_id=agent_id,
                agent_type=config.type,
            )

        return self._agents[cache_key]

    def invalidate_agent(self, agent_id: str) -> None:
        """使 Agent 缓存失效

        Args:
            agent_id: Agent ID
        """
        self._agents.pop(agent_id, None)
        self._agent_configs.pop(agent_id, None)
        logger.info("Agent 缓存已失效", agent_id=agent_id)

    def invalidate_all(self) -> None:
        """清空所有 Agent 缓存"""
        count = len(self._agents)
        self._agents = {}
        self._agent_configs = {}
        logger.info("所有 Agent 缓存已清空", count=count)

    async def chat_emit(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str,
        context: ChatContext,
        agent_id: str | None = None,
    ) -> None:
        """将聊天流事件写入 context.emitter

        Args:
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID
            context: 聊天上下文
            agent_id: 可选的 Agent ID
        """
        emitter = getattr(context, "emitter", None)
        if emitter is None or not hasattr(emitter, "aemit"):
            raise RuntimeError("chat_emit 需要 context.emitter.aemit()")

        try:
            # 获取 Agent
            agent = await self.get_agent(agent_id=agent_id)

            # 获取模型实例
            model = get_chat_model()
        except Exception as e:
            # Agent 构建失败，通知前端
            error_msg = "智能助手初始化失败，可能是依赖服务（如 Qdrant）不可用，请稍后再试"
            logger.error(
                "Agent 构建失败",
                error=str(e),
                agent_id=agent_id,
                mode=mode,
                conversation_id=conversation_id,
            )
            try:
                await emitter.aemit(
                    StreamEventType.ERROR.value,
                    {
                        "message": error_msg,
                        "detail": str(e),
                        "code": "agent_init_failed",
                    },
                )
                await emitter.aemit("__end__", None)
            except Exception:
                pass
            return

        # 使用流响应处理器
        handler = StreamingResponseHandler(
            emitter=emitter,
            model=model,
            conversation_id=conversation_id,
        )

        # 准备 Agent 输入
        agent_input = {"messages": [HumanMessage(content=message)]}
        agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}

        try:
            async for item in agent.astream(
                agent_input,
                config=agent_config,
                context=context,
                stream_mode="messages",
            ):
                msg = item[0] if isinstance(item, (tuple, list)) and item else item
                await handler.handle_message(msg)

            await handler.finalize()

            # 发送最终的 todos
            try:
                final_state = await agent.aget_state(
                    config={"configurable": {"thread_id": conversation_id}}
                )
                todos = final_state.values.get("todos")
                if todos:
                    await emitter.aemit(StreamEventType.ASSISTANT_TODOS.value, {"todos": todos})
            except Exception as e:
                logger.warning("发送最终 todos 失败", error=str(e))

        except Exception as e:
            logger.exception("chat_emit 失败", error=str(e), conversation_id=conversation_id)
            try:
                await emitter.aemit(StreamEventType.ERROR.value, {"message": str(e)})
            except Exception:
                pass
        finally:
            try:
                await emitter.aemit("__end__", None)
            except Exception:
                pass

    async def get_history(
        self,
        conversation_id: str,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取会话历史"""
        agent = await self.get_agent(agent_id=agent_id)

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
