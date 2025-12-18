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
    guide_user,
)
from app.services.agent.middleware.logging import LoggingMiddleware
from app.services.agent.middleware.intent_recognition import IntentRecognitionMiddleware
from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware
from app.services.agent.middleware.llm_call_sse import SSEMiddleware
from app.services.agent.middleware.strict_mode import StrictModeMiddleware
from app.services.streaming.context import ChatContext
from app.schemas.events import StreamEventType
from app.schemas.recommendation import RecommendationResult

logger = get_logger("agent")

# ========== 聊天模式对应的 System Prompt ==========

NATURAL_SYSTEM_PROMPT = """你是一个专业的商品推荐助手，具备强大的商品检索和分析能力。

## 核心职责
1. 理解用户的购物需求和偏好
2. 使用合适的工具进行商品检索和分析
3. 提供个性化的商品推荐和专业建议

## 可用工具
1. **search_products** - 根据需求搜索商品
2. **get_product_details** - 获取商品详细信息
3. **compare_products** - 对比多个商品的优劣
4. **filter_by_price** - 按价格区间过滤商品
5. **guide_user** - 当信息不足/无法命中商品时，生成澄清问题与下一步建议

## 工作流程
1. **理解需求**：仔细分析用户的具体需求
2. **选择策略**：根据需求选择合适的工具组合
3. **执行检索**：使用工具获取商品信息
4. **分析对比**：如果用户需要对比，使用 compare_products
5. **生成推荐**：基于结果给出专业建议

## 推荐原则
- 只推荐搜索结果中存在的商品
- 突出商品的核心卖点和性价比
- 每次推荐 2-3 个商品（除非用户要求更多）
- 如果用户需要对比，先搜索再对比
- 如果用户有价格预算，使用 filter_by_price
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

## 核心能力
1. 可以回答各类问题（知识、建议、闲聊等）
2. 具备商品检索和推荐能力（当用户有购物需求时使用）
3. 保持自然、友好的对话风格

## 可用工具（按需使用）
1. **search_products** - 根据需求搜索商品
2. **get_product_details** - 获取商品详细信息
3. **compare_products** - 对比多个商品的优劣
4. **filter_by_price** - 按价格区间过滤商品
5. **guide_user** - 当需要澄清用户需求时，生成引导问题

## 行为准则
- 如果用户有购物需求，主动使用工具帮助检索
- 如果用户只是闲聊或问知识性问题，直接回答即可
- 不要强行引导用户回到商品话题
- 保持真诚、有帮助的态度
- 不确定的信息要明确说明，不要编造

## 重要约束
- 推荐商品时，只推荐工具返回的真实商品
- 不要编造不存在的商品信息
"""

STRICT_SYSTEM_PROMPT = """你是一个严谨的商品推荐助手，所有回答必须有据可依。

## 核心原则（必须严格遵守）
1. **必须使用工具**：回答商品相关问题前，必须先调用工具获取数据
2. **必须有据可依**：所有推荐和建议必须基于工具返回的真实数据
3. **禁止无依据回答**：如果没有调用工具或工具没有返回有效数据，不要给出推荐

## 可用工具（必须使用）
1. **search_products** - 根据需求搜索商品
2. **get_product_details** - 获取商品详细信息
3. **compare_products** - 对比多个商品的优劣
4. **filter_by_price** - 按价格区间过滤商品
5. **guide_user** - 当信息不足/无法命中商品时，生成澄清问题与下一步建议

## 工作流程
1. 收到用户请求后，**必须先调用相关工具**
2. 根据工具返回的数据进行分析
3. 基于真实数据给出推荐和建议

## 信息不足时的处理
如果用户的请求信息不足以进行有效检索，你应该：
1. 优先调用 **guide_user** 工具生成澄清问题
2. 仅在拿到足够条件后，再调用商品检索/对比工具
3. 不要在没有数据支撑的情况下给出推荐

## 输出要求
- 推荐商品时必须引用工具返回的具体数据（名称、价格、特点等）
- 不要编造任何商品信息
- 如果工具没有找到合适的商品，如实告知用户
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

    def __new__(cls) -> "AgentService":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
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

    async def get_agent(
        self,
        mode: str = "natural",
        use_todo_middleware: bool = False,
        use_structured_output: bool = False,
        use_intent_recognition: bool = True,
    ) -> CompiledStateGraph:
        """获取 Agent 实例

        Args:
            mode: 聊天模式（natural/free/strict）
            use_todo_middleware: 是否使用任务规划中间件
            use_structured_output: 是否使用结构化输出
            use_intent_recognition: 是否使用意图识别中间件（默认启用）

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

            # 意图识别中间件：natural 模式启用，free 模式禁用（不做工具过滤）
            # strict 模式也启用（但不会过滤掉工具）
            if use_intent_recognition and mode != "free":
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

            # strict 模式：添加 StrictModeMiddleware（放在最后，对最终响应做检查）
            if mode == "strict":
                middlewares.append(StrictModeMiddleware())

            # 获取对应模式的 system prompt
            system_prompt = self._get_system_prompt(mode)

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
        - Orchestrator 作为唯一对外 SSE 出口：从 queue 读取 domain events -> make_event -> encode_sse
        - 推理内容按“字符”拆分后逐条发送，达到逐字蹦出的效果
        """
        mode = getattr(context, "mode", "natural")
        agent = await self.get_agent(mode=mode)

        emitter = getattr(context, "emitter", None)
        if emitter is None or not hasattr(emitter, "aemit"):
            raise RuntimeError("chat_emit 需要 context.emitter.aemit()（用于高频不丢事件）")

        full_content = ""
        full_reasoning = ""
        products_data: Any | None = None
        seen_tool_message_ids: set[str] = set()
        has_content_started = False

        # 准备 Agent 输入
        agent_input = {"messages": [HumanMessage(content=message)]}
        agent_config: dict[str, Any] = {"configurable": {"thread_id": conversation_id}}
        
        # agent_config["metadata"] = {"chat_context": context}

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
                        # 约定：reasoning_content 永远作为“思考”推送，避免 Markdown/关键词启发式误判导致混流
                        full_reasoning += rk
                        reasoning_char_count += len(rk)
                        reasoning_event_count += 1
                        await emitter.aemit(
                            StreamEventType.ASSISTANT_REASONING_DELTA.value,
                            {"delta": rk},
                        )

                # 1.1) 部分模型/版本会在流末尾给出完整 AIMessage（非 chunk）
                # 这种情况下 content 可能为空，但 reasoning_content 有值。
                # 为避免“最终 content 为空”，这里在尚未收到任何增量时兜底吸收一次。
                elif isinstance(msg, AIMessage):
                    if content_event_count == 0:
                        delta = msg.content or ""
                        if isinstance(delta, list):
                            delta = "".join(str(x) for x in delta)
                        if isinstance(delta, str) and delta:
                            has_content_started = True
                            full_content += delta
                            content_event_count += 1
                            await emitter.aemit(
                                StreamEventType.ASSISTANT_DELTA.value,
                                {"delta": delta},
                            )

                    if reasoning_event_count == 0:
                        rk = (
                            (getattr(msg, "additional_kwargs", None) or {}).get("reasoning_content")
                            or ""
                        )
                        if isinstance(rk, str) and rk:
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
            # 兜底：仅当“全程没有任何 content delta”时，才把 reasoning 兜底成 content（避免混流）
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
