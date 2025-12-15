"""LangChain v1.1 Agent 服务"""

import json
from collections.abc import AsyncGenerator
import profile
from typing import Any

import aiosqlite
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from app.core.models_dev import get_model_profile

from app.core.config import settings
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.services.agent.tools import search_products

logger = get_logger("agent")

SYSTEM_PROMPT = """你是一个专业的商品推荐助手。

## 职责
1. 理解用户的购物需求
2. 使用 search_products 工具搜索匹配的商品
3. 基于搜索结果，推荐最合适的商品并说明理由

## 规则
- 只推荐搜索结果中存在的商品
- 如果没有匹配商品，诚实告知用户
- 回复简洁，突出商品核心卖点和价格
- 每次最多推荐 3 个商品
- 使用友好的语气，像朋友一样交流

## 输出格式
当推荐商品时，请使用以下格式：

根据您的需求，我为您推荐以下商品：

1. **商品名称** - ¥价格
   - 推荐理由

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
                logger.warning("检测到连接失效，重新创建 checkpointer")
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
        logger.debug("创建 SQLite checkpointer", path=self._checkpoint_path)
        
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
        except (AttributeError, TypeError) as e:
            # 如果无法设置方法（某些连接对象可能不允许），记录警告但继续
            logger.debug("无法设置 is_alive 方法", error=str(e))
        
        self._checkpointer = AsyncSqliteSaver(self._conn)
        # 初始化数据库表（必需）
        await self._checkpointer.setup()
        logger.debug("SQLite checkpointer 初始化完成")
        
        return self._checkpointer

    async def close(self) -> None:
        """关闭连接"""
        if self._conn:
            try:
                await self._conn.close()
            except Exception as e:
                logger.warning("关闭连接时出错", error=str(e))
            finally:
                self._conn = None
                self._checkpointer = None
                self._agent = None
                logger.info("Agent 连接已关闭")

    async def get_agent(self) -> CompiledStateGraph:
        """获取 Agent 实例"""
        if self._agent is None:
            logger.info("初始化 Agent...")
            
            # 初始化模型
            model = get_chat_model()
            
            # 初始化 checkpointer
            checkpointer = await self._get_checkpointer()
            
            # 创建 Agent
            self._agent = create_agent(
                model=model,
                tools=[search_products],
                system_prompt=SYSTEM_PROMPT,
                checkpointer=checkpointer,
            )
            
            logger.info("Agent 初始化完成")
        
        return self._agent

    async def chat(
        self,
        message: str,
        conversation_id: str,
        user_id: str,
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
        
        # ===== 步骤 1: 接收请求 =====
        logger.info(
            "═══ [1/5] 接收用户请求 ═══",
            input_data={
                "message": message,
                "message_length": len(message),
                "conversation_id": conversation_id,
                "user_id": user_id,
            },
        )
        
        full_content = ""
        reasoning_content = ""  # 累积推理内容
        products_data = None
        chunk_count = 0
        tool_calls = []
        
        try:
            # ===== 步骤 2: 准备 Agent 输入 =====
            agent_input = {"messages": [HumanMessage(content=message)]}
            agent_config = {"configurable": {"thread_id": conversation_id}}
            
            logger.info(
                "═══ [2/5] 准备 Agent 输入 ═══",
                agent_input={
                    "messages": [{"type": "HumanMessage", "content": message}],
                },
                config=agent_config,
            )
            
            # ===== 步骤 3: 流式处理事件 =====
            logger.info("═══ [3/5] 开始流式处理 ═══")
            
            async for event in agent.astream_events(
                agent_input,
                config=agent_config,
                version="v2",
            ):
                print(f"on_chat_model_stream event: {event}")
                event_type = event.get("event")
                event_name = event.get("name", "")
                
                # 记录所有事件类型（调试用）
                if event_type not in ("on_chat_model_stream",):  # 跳过频繁的流式事件
                    logger.debug(
                        f"事件: {event_type}",
                        event_name=event_name,
                        event_keys=list(event.keys()),
                    )
                
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
                                "type": "reasoning",
                                "content": chunk_reasoning,
                            }
                        
                        # 处理普通文本内容
                        if hasattr(chunk, "content") and chunk.content:
                            content = chunk.content
                            full_content += content
                            chunk_count += 1
                            
                            yield {
                                "type": "text",
                                "content": content,
                            }
                
                # 处理工具调用开始
                elif event_type == "on_tool_start":
                    tool_input = event.get("data", {}).get("input", {})
                    logger.info(
                        "───  工具调用开始 ───",
                        tool_name=event_name,
                        tool_input=tool_input,
                    )
                    tool_calls.append({
                        "name": event_name,
                        "input": tool_input,
                        "status": "started",
                    })
                
                # 处理工具调用结束
                elif event_type == "on_tool_end":
                    output = event.get("data", {}).get("output")
                    
                    logger.info(
                        "───  工具调用结束 ───",
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
                                logger.warning(
                                    "未知的工具输出类型",
                                    output_type=type(output).__name__,
                                    output_repr=repr(output)[:200],
                                )
                                continue
                            
                            logger.info(
                                "───  商品数据解析成功 ───",
                                product_count=len(products_data) if isinstance(products_data, list) else 1,
                                products=[
                                    {"id": p.get("id"), "name": p.get("name"), "price": p.get("price")}
                                    for p in (products_data if isinstance(products_data, list) else [products_data])
                                ],
                            )
                            yield {
                                "type": "products",
                                "data": products_data,
                            }
                        except json.JSONDecodeError as e:
                            logger.error(
                                "JSON 解析失败",
                                exc_info=True,
                                output_preview=str(output)[:200],
                                error=str(e),
                            )
                        except Exception as e:
                            logger.error(
                                "处理工具输出失败",
                                exc_info=True,
                                error=str(e),
                            )
                
                # 处理链开始/结束
                elif event_type == "on_chain_start":
                    if event_name not in ("RunnableSequence",):  # 过滤噪音
                        logger.debug(
                            "链开始",
                            chain_name=event_name,
                        )
                elif event_type == "on_chain_end":
                    if event_name not in ("RunnableSequence",):
                        logger.debug(
                            "链结束",
                            chain_name=event_name,
                        )
            
            # ===== 步骤 4: 流式处理完成统计 =====
            logger.info(
                "═══ [4/5] 流式处理完成 ═══",
                stats={
                    "total_chunks": chunk_count,
                    "response_length": len(full_content),
                    "reasoning_length": len(reasoning_content),
                    "has_reasoning": len(reasoning_content) > 0,
                    "tool_calls_count": len(tool_calls),
                    "has_products": products_data is not None,
                },
            )
            
            # ===== 步骤 5: 发送完成事件 =====
            done_event = {
                "type": "done",
                "content": full_content,
                "reasoning": reasoning_content if reasoning_content else None,
                "products": products_data,
            }
            
            logger.info(
                "═══ [5/5] 聊天完成 ═══",
                output_data={
                    "content_preview": full_content[:200] + "..." if len(full_content) > 200 else full_content,
                    "content_length": len(full_content),
                    "reasoning_length": len(reasoning_content),
                    "has_reasoning": len(reasoning_content) > 0,
                    "product_count": len(products_data) if isinstance(products_data, list) else (1 if products_data else 0),
                    "tool_calls": tool_calls,
                },
            )
            
            yield done_event
            
        except Exception as e:
            logger.exception(
                "═══ [ERROR] 聊天过程中发生错误 ═══",
                error=str(e),
                error_type=type(e).__name__,
                context={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "chunks_processed": chunk_count,
                },
            )
            raise

    async def get_history(self, conversation_id: str) -> list[dict[str, Any]]:
        """获取会话历史"""
        agent = await self.get_agent()
        
        try:
            state = await agent.aget_state(
                config={"configurable": {"thread_id": conversation_id}}
            )
            
            messages = state.values.get("messages", [])
            history = []
            
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    history.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    history.append({"role": "assistant", "content": msg.content})
            
            logger.debug("获取历史成功", conversation_id=conversation_id, count=len(history))
            return history
        except Exception as e:
            logger.error("获取历史失败", exc_info=True, conversation_id=conversation_id, error=str(e))
            return []


# 全局单例
agent_service = AgentService()
