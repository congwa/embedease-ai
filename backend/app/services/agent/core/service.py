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
from typing import Any

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.database import get_db_context
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.schemas.agent import AgentConfig
from app.schemas.events import StreamEventType
from app.services.agent.core.config import AgentConfigLoader, get_or_create_default_agent
from app.services.agent.core.factory import build_agent
from app.services.agent.streams import StreamingResponseHandler
from app.services.streaming.context import ChatContext

logger = get_logger("agent.service")


class AgentService:
    """Agent 服务 - 管理多 Agent 的生命周期

    缓存键：(agent_id, mode)
    """

    _instance: "AgentService | None" = None
    _agents: dict[tuple[str, str], CompiledStateGraph]  # (agent_id, mode) -> agent
    _agent_configs: dict[tuple[str, str], AgentConfig]  # (agent_id, mode) -> config
    _checkpointer: AsyncSqliteSaver | None = None
    _conn: aiosqlite.Connection | None = None
    _checkpoint_path: str | None = None
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

    async def _get_checkpointer(self) -> AsyncSqliteSaver:
        """获取 checkpointer"""
        if self._checkpointer is not None and self._conn is not None:
            try:
                await self._conn.execute("SELECT 1")
                return self._checkpointer
            except Exception:
                self._checkpointer = None
                if self._conn:
                    try:
                        await self._conn.close()
                    except Exception:
                        pass
                self._conn = None

        settings.ensure_data_dir()
        self._checkpoint_path = settings.CHECKPOINT_DB_PATH

        self._conn = await aiosqlite.connect(
            self._checkpoint_path,
            isolation_level=None,
        )

        try:
            if not hasattr(self._conn, "is_alive"):
                import types

                def is_alive(conn) -> bool:  # noqa: ARG001
                    return True

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
        mode: str = "natural",
    ) -> AgentConfig:
        """获取 Agent 配置

        Args:
            agent_id: Agent ID，为空时使用默认 Agent
            mode: 回答策略模式

        Returns:
            Agent 运行时配置
        """
        if agent_id is None:
            agent_id = await self.get_default_agent_id()

        cache_key = (agent_id, mode)

        # 检查缓存
        if cache_key in self._agent_configs:
            cached_config = self._agent_configs[cache_key]
            # TODO: 检查版本是否过期
            return cached_config

        # 从数据库加载
        async with get_db_context() as session:
            loader = AgentConfigLoader(session)
            config = await loader.load_config(agent_id, mode)

        if config is None:
            raise ValueError(f"Agent 不存在或已禁用: {agent_id}")

        # 缓存配置
        self._agent_configs[cache_key] = config
        return config

    async def get_agent(
        self,
        agent_id: str | None = None,
        mode: str = "natural",
        use_structured_output: bool = False,
    ) -> CompiledStateGraph:
        """获取 Agent 实例

        Args:
            agent_id: Agent ID，为空时使用默认 Agent
            mode: 回答策略模式
            use_structured_output: 是否使用结构化输出

        Returns:
            编译后的 Agent 图
        """
        if agent_id is None:
            agent_id = await self.get_default_agent_id()

        cache_key = (agent_id, mode)

        if cache_key not in self._agents:
            # 加载配置
            config = await self.get_agent_config(agent_id, mode)

            # 获取 checkpointer
            checkpointer = await self._get_checkpointer()

            # 构建 Agent
            agent = await build_agent(
                config=config,
                checkpointer=checkpointer,
                use_structured_output=use_structured_output,
            )

            self._agents[cache_key] = agent
            logger.info(
                "创建 Agent 实例",
                agent_id=agent_id,
                mode=mode,
                agent_type=config.type,
            )

        return self._agents[cache_key]

    def invalidate_agent(self, agent_id: str, mode: str | None = None) -> None:
        """使 Agent 缓存失效

        Args:
            agent_id: Agent ID
            mode: 可选的模式，为空时清除该 agent 的所有模式缓存
        """
        if mode:
            cache_key = (agent_id, mode)
            self._agents.pop(cache_key, None)
            self._agent_configs.pop(cache_key, None)
        else:
            # 清除该 agent 的所有缓存
            keys_to_remove = [k for k in self._agents if k[0] == agent_id]
            for key in keys_to_remove:
                self._agents.pop(key, None)
                self._agent_configs.pop(key, None)

        logger.info("Agent 缓存已失效", agent_id=agent_id, mode=mode)

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
        mode = getattr(context, "mode", "natural")
        
        emitter = getattr(context, "emitter", None)
        if emitter is None or not hasattr(emitter, "aemit"):
            raise RuntimeError("chat_emit 需要 context.emitter.aemit()")

        try:
            # 获取 Agent
            agent = await self.get_agent(agent_id=agent_id, mode=mode)

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
                    }
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
