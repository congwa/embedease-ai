"""LangChain v1.1 Agent 服务"""

import json
import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import aiosqlite
from langchain.agents import create_agent
from langchain.agents.middleware.todo import TodoListMiddleware
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
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
from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware
from app.services.agent.middleware.sse_events import SSEMiddleware
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
            # 中间件职责拆分：
            # - ResponseSanitizationMiddleware：检测并清洗异常响应格式（最先处理响应）
            # - SSEMiddleware：只负责 llm.call.start/end 事件推送（前端可用于 Debug/性能）
            # - LoggingMiddleware：只负责 logger 记录（不发送任何 SSE 事件）
            middlewares = [
                ResponseSanitizationMiddleware(
                    enabled=settings.RESPONSE_SANITIZATION_ENABLED,
                    custom_fallback_message=settings.RESPONSE_SANITIZATION_CUSTOM_MESSAGE,
                ),
                SSEMiddleware(),
                LoggingMiddleware(),
            ]

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
                    # 启用 LangGraph 标准 context 注入：invoke/stream 时传入的 context 会被注入到 Runtime.context，
                    # ToolNode 会进一步注入到 ToolRuntime.context，供 tools/middleware 使用。
                    "context_schema": ChatContext,
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
        last_ai_text = ""
        last_reasoning_text = ""
        seen_message_ids: set[str] = set()

        try:
            # 准备 Agent 输入
            agent_input = {"messages": [HumanMessage(content=message)]}
            agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
            if context is not None:
                agent_config["metadata"] = {"chat_context": context}

            # 使用 LangGraph 标准流式接口：context 会被注入到 Runtime.context / ToolRuntime.context
            async for state in agent.astream(
                agent_input,
                config=agent_config,
                context=context
            ):
                # stream_mode="values" 时，state 是完整 state dict
                # stream_mode="values,messages" 时，state 是完整 state dict 和 messages 列表
                messages = state.get("messages") if isinstance(state, dict) else None
                if not isinstance(messages, list):
                    continue

                # 1) 从最新 AIMessage 生成 assistant.delta / assistant.reasoning.delta
                last_ai: AIMessage | None = None
                for m in reversed(messages):
                    if isinstance(m, AIMessage):
                        last_ai = m
                        break

                if last_ai is not None:
                    current_text = last_ai.content or ""
                    if isinstance(current_text, list):
                        # content_blocks 场景：这里只做简单兜底
                        current_text = "".join(str(x) for x in current_text)

                    if isinstance(current_text, str) and current_text.startswith(last_ai_text):
                        delta = current_text[len(last_ai_text) :]
                    else:
                        # 非严格前缀（例如模型重写），直接以全量覆盖追加
                        delta = current_text

                    if delta:
                        last_ai_text = current_text
                        full_content = current_text
                        chunk_count += 1
                        yield {
                            "type": StreamEventType.ASSISTANT_DELTA.value,
                            "payload": {"delta": delta},
                        }

                    current_reasoning = ""
                    if getattr(last_ai, "additional_kwargs", None):
                        current_reasoning = last_ai.additional_kwargs.get("reasoning_content") or ""
                    if current_reasoning and isinstance(current_reasoning, str):
                        if current_reasoning.startswith(last_reasoning_text):
                            r_delta = current_reasoning[len(last_reasoning_text) :]
                        else:
                            r_delta = current_reasoning
                        if r_delta:
                            last_reasoning_text = current_reasoning
                            reasoning_content = current_reasoning
                            yield {
                                "type": StreamEventType.ASSISTANT_REASONING_DELTA.value,
                                "payload": {"delta": r_delta},
                            }

                # 2) 从新增 ToolMessage 解析 products，并发 assistant.products
                for m in messages:
                    if not isinstance(m, ToolMessage):
                        continue
                    msg_id = getattr(m, "id", None)
                    if isinstance(msg_id, str) and msg_id in seen_message_ids:
                        continue
                    if isinstance(msg_id, str):
                        seen_message_ids.add(msg_id)

                    content = m.content
                    try:
                        if isinstance(content, str):
                            products_data = json.loads(content)
                        elif isinstance(content, (list, dict)):
                            products_data = content
                        else:
                            continue
                        yield {
                            "type": StreamEventType.ASSISTANT_PRODUCTS.value,
                            "payload": {
                                "items": products_data if isinstance(products_data, list) else [products_data]
                            },
                        }
                    except Exception:
                        continue

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
        - Orchestrator 作为唯一对外 SSE 出口：从 queue 读取 domain events -> make_event -> encode_sse
        - 推理内容按“字符”拆分后逐条发送，达到逐字蹦出的效果
        """
        agent = await self.get_agent()

        emitter = getattr(context, "emitter", None)
        if emitter is None or not hasattr(emitter, "aemit"):
            raise RuntimeError("chat_emit 需要 context.emitter.aemit()（用于高频不丢事件）")

        def _looks_like_final_content(text: str) -> bool:
            """启发式判断：某些 provider 可能把“最终回答”塞到 reasoning_content。

            如果误判，会导致把一部分思考当成 content；但相比“content 长期为空”更可控，
            且前端已经按 segments 保留时间顺序内容，不会丢失。
            """
            t = (text or "").strip()
            if not t:
                return False
            # 结构化/Markdown 强信号
            if "###" in t or "\n###" in t or "**" in t:
                return True
            # 商品推荐模板强信号
            keywords = [
                "根据您的需求",
                "我为您推荐",
                "推荐以下",
                "推荐理由",
                "适合人群",
                "推荐建议",
                "商品名称",
                "价格",
                "¥",
            ]
            if any(k in t for k in keywords):
                return True
            # 句子完整度信号：包含多行/长段落更像最终输出
            if "\n" in t and len(t) >= 80:
                return True
            return False

        full_content = ""
        full_reasoning = ""
        products_data: Any | None = None
        seen_tool_message_ids: set[str] = set()
        has_content_started = False

        # 准备 Agent 输入
        agent_input = {"messages": [HumanMessage(content=message)]}
        agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
        agent_config["metadata"] = {"chat_context": context}

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

                # 1) 模型 chunk：正文按 chunk 推送；推理按字符推送
                if isinstance(msg, AIMessageChunk):
                    # 正文增量
                    delta = msg.content or ""
                    if isinstance(delta, list):
                        delta = "".join(str(x) for x in delta)
                    if isinstance(delta, str) and delta:
                        has_content_started = True
                        # 不做逐字拆分：模型返回多长增量，就推多长
                        full_content += delta
                        content_event_count += 1
                        await emitter.aemit(
                            StreamEventType.ASSISTANT_DELTA.value,
                            {"delta": delta},
                        )

                    # 推理增量（推理模型会写入 additional_kwargs.reasoning_content）
                    rk = (
                        (getattr(msg, "additional_kwargs", None) or {}).get("reasoning_content")
                        or ""
                    )
                    if isinstance(rk, str) and rk:
                        # 关键：区分 rk 是“思考”还是“最终内容”
                        route_to_content = (not has_content_started) and _looks_like_final_content(rk)
                        if route_to_content:
                            # provider 把最终回答塞进 reasoning_content：把它当 content 推送
                            has_content_started = True
                            full_content += rk
                            content_event_count += 1
                            await emitter.aemit(
                                StreamEventType.ASSISTANT_DELTA.value,
                                {"delta": rk},
                            )
                        else:
                            full_reasoning += rk
                            reasoning_char_count += len(rk)
                            reasoning_event_count += 1
                            await emitter.aemit(
                                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                                {"delta": rk},
                            )

                # 2) 工具消息：解析 products（保持你现有协议）
                elif isinstance(msg, ToolMessage):
                    msg_id = getattr(msg, "id", None)
                    if isinstance(msg_id, str) and msg_id in seen_tool_message_ids:
                        continue
                    if isinstance(msg_id, str):
                        seen_tool_message_ids.add(msg_id)

                    content = msg.content
                    try:
                        if isinstance(content, str):
                            products_data = json.loads(content)
                        elif isinstance(content, (list, dict)):
                            products_data = content
                        else:
                            continue

                        await emitter.aemit(
                            StreamEventType.ASSISTANT_PRODUCTS.value,
                            {
                                "items": products_data
                                if isinstance(products_data, list)
                                else [products_data]
                            },
                        )
                    except Exception:
                        continue

            # 发送完成事件（final 用于 Orchestrator 聚合 + 落库对齐）
            # 兜底：如果 content 太短但 reasoning 很长，说明 provider 可能把最终输出塞进了 reasoning。
            if len(full_content) < 20 and len(full_reasoning) > 120:
                logger.warning(
                    "检测到 content 过短而 reasoning 过长，兜底将 reasoning 作为 content 输出",
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
