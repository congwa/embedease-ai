"""LangChain v1.1 Agent 服务"""

import json
from collections.abc import AsyncGenerator
from typing import Any

import aiosqlite
from langchain.agents import create_agent
from langchain.agents.middleware.todo import TodoListMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.services.agent.tools import (
    search_products,
    get_product_details,
    compare_products,
    filter_by_price,
)
from app.services.agent.middleware.logging import LoggingMiddleware
from app.services.agent.middleware.intent_recognition import IntentRecognitionMiddleware
from app.services.streaming.context import ChatContext
from app.schemas.events import StreamEventType
from app.schemas.recommendation import RecommendationResult

logger = get_logger("agent")

SYSTEM_PROMPT = """你是一个专业的商品推荐助手，具备强大的商品检索和分析能力。

## 核心职责
1. 理解用户的购物需求和偏好
2. 使用合适的工具进行商品检索和分析
3. 提供个性化的商品推荐和专业建议

## 可用工具
1. **search_products** - 根据需求搜索商品
2. **get_product_details** - 获取商品详细信息
3. **compare_products** - 对比多个商品的优劣
4. **filter_by_price** - 按价格区间过滤商品

## 工作流程
1. **理解需求**：仔细分析用户的具体需求
2. **选择策略**：根据需求选择合适的工具组合
3. **执行检索**：使用工具获取商品信息
4. **分析对比**：如果用户需要对比，使用 compare_products
5. **生成推荐**：基于结果给出专业建议

## 推荐原则
- ✅ 只推荐搜索结果中存在的商品
- ✅ 突出商品的核心卖点和性价比
- ✅ 每次推荐 2-3 个商品（除非用户要求更多）
- ✅ 如果用户需要对比，先搜索再对比
- ✅ 如果用户有价格预算，使用 filter_by_price
- ✅ 保持友好、专业的语气

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


class AgentService:
    """Agent 服务 - 管理 LangChain Agent 的生命周期"""

    _instance: "AgentService | None" = None
    _agent: CompiledStateGraph | None = None
    _checkpointer: AsyncSqliteSaver | None = None
    _conn: aiosqlite.Connection | None = None
    _checkpoint_path: str | None = None

    def __new__(cls) -> "AgentService":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
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
                self._agent = None

    async def get_agent(
        self,
        use_todo_middleware: bool = False,
        use_structured_output: bool = False,
        use_intent_recognition: bool = True,
    ) -> CompiledStateGraph:
        """获取 Agent 实例

        Args:
            use_todo_middleware: 是否使用任务规划中间件
            use_structured_output: 是否使用结构化输出
            use_intent_recognition: 是否使用意图识别中间件（默认启用）

        Returns:
            编译后的 Agent 图
        """
        if self._agent is None:
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
            ]

            # 准备中间件列表
            middlewares = [LoggingMiddleware()]

            # 可选：添加意图识别中间件（放在最前面，优先执行）
            if use_intent_recognition:
                try:
                    middlewares.insert(0, IntentRecognitionMiddleware())
                except Exception:
                    pass

            # 可选：添加任务规划中间件
            if use_todo_middleware:
                try:
                    middlewares.append(TodoListMiddleware())
                except Exception:
                    pass

            # 创建 Agent
            try:
                agent_kwargs = {
                    "model": model,
                    "tools": tools,
                    "system_prompt": SYSTEM_PROMPT,
                    "checkpointer": checkpointer,
                    "middleware": middlewares,
                    # 移除 context_schema 以避免 Pydantic JsonSchema 生成问题
                    # ToolRuntime 会自动处理 context 注入
                }

                # 可选：使用结构化输出
                if use_structured_output:
                    agent_kwargs["response_format"] = RecommendationResult

                self._agent = create_agent(**agent_kwargs)

            except TypeError:
                # 兼容较老版本：不支持某些参数时回退
                self._agent = create_agent(
                    model=model,
                    tools=tools,
                    system_prompt=SYSTEM_PROMPT,
                    checkpointer=checkpointer,
                )

        return self._agent

    async def chat(
        self,
        message: str,
        conversation_id: str,
        user_id: str,
        context: ChatContext | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """流式聊天

        Args:
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID

        Yields:
            聊天事件
        """
        agent = await self.get_agent()

        full_content = ""
        reasoning_content = ""  # 累积推理内容
        products_data = None
        chunk_count = 0
        tool_calls = []

        try:
            # 准备 Agent 输入
            agent_input = {"messages": [HumanMessage(content=message)]}
            agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
            if context is not None:
                agent_config["metadata"] = {"chat_context": context}

            try:
                event_iter = agent.astream_events(
                    agent_input,
                    config=agent_config,
                    version="v2",
                    context=context,
                )
            except TypeError:
                logger.warning("astream_events 不支持 context 参数，将忽略 context 注入")
                event_iter = agent.astream_events(
                    agent_input,
                    config=agent_config,
                    version="v2",
                )

            async for event in event_iter:
                event_type = event.get("event")
                event_name = event.get("name", "")

                # 处理模型流式输出
                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        # 处理推理内容（如果存在）
                        chunk_reasoning = None
                        if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                            chunk_reasoning = chunk.additional_kwargs.get("reasoning_content")

                        # 累积推理内容
                        if chunk_reasoning:
                            reasoning_content += chunk_reasoning
                            yield {
                                "type": StreamEventType.ASSISTANT_REASONING_DELTA.value,
                                "payload": {"delta": chunk_reasoning},
                            }

                        # 处理普通文本内容
                        if hasattr(chunk, "content") and chunk.content:
                            content = chunk.content
                            full_content += content
                            chunk_count += 1

                            yield {
                                "type": StreamEventType.ASSISTANT_DELTA.value,
                                "payload": {"delta": content},
                            }

                # 处理工具调用开始
                elif event_type == "on_tool_start":
                    tool_input = event.get("data", {}).get("input", {})
                    logger.info(
                        "🔧 工具调用开始",
                        tool_name=event_name,
                        tool_input=tool_input,
                    )
                    tool_calls.append(
                        {
                            "name": event_name,
                            "input": tool_input,
                            "status": "started",
                        }
                    )

                # 处理工具调用结束
                elif event_type == "on_tool_end":
                    output = event.get("data", {}).get("output")

                    logger.info(
                        "✅ 工具调用结束",
                        tool_name=event_name,
                        output_type=type(output).__name__,
                        output_preview=str(output)[:300] if output else None,
                    )

                    # 更新工具调用状态
                    for tc in tool_calls:
                        if tc["name"] == event_name and tc["status"] == "started":
                            tc["status"] = "completed"
                            tc["output_type"] = type(output).__name__
                            break

                    if output:
                        try:
                            # 处理不同类型的输出
                            if isinstance(output, str):
                                products_data = json.loads(output)
                            elif isinstance(output, ToolMessage):
                                content = output.content
                                if isinstance(content, str):
                                    products_data = json.loads(content)
                                else:
                                    products_data = content
                            elif isinstance(output, (list, dict)):
                                products_data = output
                            else:
                                continue
                            yield {
                                "type": StreamEventType.ASSISTANT_PRODUCTS.value,
                                "payload": {
                                    "items": products_data
                                    if isinstance(products_data, list)
                                    else [products_data]
                                },
                            }
                        except (json.JSONDecodeError, Exception):
                            pass

            # 发送完成事件
            yield {
                "type": StreamEventType.ASSISTANT_FINAL.value,
                "payload": {
                    "content": full_content,
                    "reasoning": reasoning_content if reasoning_content else None,
                    "products": products_data
                    if isinstance(products_data, list) or products_data is None
                    else [products_data],
                },
            }

        except Exception as e:
            logger.exception("❌ 聊天失败", error=str(e))
            raise

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
