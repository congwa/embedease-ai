"""ChatStreamKit - 主入口类"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any, TYPE_CHECKING

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.core.stream_event import StreamEvent
from langgraph_agent_kit.core.context import ChatContext
from langgraph_agent_kit.core.emitter import QueueDomainEmitter
from langgraph_agent_kit.streaming.sse import make_event
from langgraph_agent_kit.streaming.response_handler import StreamingResponseHandler
from langgraph_agent_kit.middleware.registry import MiddlewareRegistry
from langgraph_agent_kit.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from langgraph_agent_kit.middleware.base import MiddlewareSpec, BaseMiddleware
    from langgraph_agent_kit.tools.base import ToolSpec


class ChatStreamKit:
    """聊天流工具包 - 主入口类
    
    提供流畅的 API 来配置和运行流式聊天。
    
    Usage:
        kit = ChatStreamKit(
            model=my_model,
            middlewares=[Middlewares.sse_events()],
        )
        
        async for event in kit.chat_stream(
            message="你好",
            conversation_id="conv_123",
            user_id="user_456",
        ):
            print(event.type, event.payload)
    """

    def __init__(
        self,
        *,
        model: Any = None,
        agent: Any = None,
        middlewares: list["MiddlewareSpec | BaseMiddleware"] | None = None,
        tools: list["ToolSpec"] | None = None,
        event_queue_size: int = 10000,
    ):
        """初始化 ChatStreamKit
        
        Args:
            model: LangChain 模型实例
            agent: LangGraph Agent 实例（可选，如果提供则忽略 model）
            middlewares: 中间件列表
            tools: 工具列表
            event_queue_size: 事件队列大小
        """
        self._model = model
        self._agent = agent
        self._event_queue_size = event_queue_size
        
        self._middleware_registry = MiddlewareRegistry()
        self._tool_registry = ToolRegistry()
        
        if middlewares:
            for middleware in middlewares:
                self._middleware_registry.register(middleware)
        
        if tools:
            for tool in tools:
                self._tool_registry.register(tool)

    @property
    def middlewares(self) -> MiddlewareRegistry:
        """获取中间件注册表"""
        return self._middleware_registry

    @property
    def tools(self) -> ToolRegistry:
        """获取工具注册表"""
        return self._tool_registry

    def add_middleware(self, middleware: "MiddlewareSpec | BaseMiddleware") -> "ChatStreamKit":
        """添加中间件（链式调用）"""
        self._middleware_registry.register(middleware)
        return self

    def add_tool(self, tool: "ToolSpec") -> "ChatStreamKit":
        """添加工具（链式调用）"""
        self._tool_registry.register(tool)
        return self

    async def chat_stream(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str,
        assistant_message_id: str | None = None,
        user_message_id: str | None = None,
        context_data: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """流式聊天
        
        Args:
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID
            assistant_message_id: 助手消息 ID（可选，自动生成）
            user_message_id: 用户消息 ID（可选）
            context_data: 额外的上下文数据
        
        Yields:
            StreamEvent 事件
        """
        import uuid
        
        if assistant_message_id is None:
            assistant_message_id = str(uuid.uuid4())
        
        seq = 0
        
        def next_seq() -> int:
            nonlocal seq
            seq += 1
            return seq
        
        yield make_event(
            seq=next_seq(),
            conversation_id=conversation_id,
            message_id=assistant_message_id,
            type=StreamEventType.META_START.value,
            payload={
                "user_message_id": user_message_id,
                "assistant_message_id": assistant_message_id,
            },
        )

        try:
            loop = asyncio.get_running_loop()
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
                maxsize=self._event_queue_size
            )
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)

            context = ChatContext(
                conversation_id=conversation_id,
                user_id=user_id,
                assistant_message_id=assistant_message_id,
                emitter=emitter,
            )

            handler = StreamingResponseHandler(
                emitter=emitter,
                model=self._model,
                conversation_id=conversation_id,
            )

            async def run_agent() -> None:
                if self._agent:
                    async for chunk in self._agent.astream(
                        {"messages": [{"role": "user", "content": message}]},
                        config={"configurable": {"thread_id": conversation_id}},
                        context=context,
                    ):
                        if "messages" in chunk:
                            for msg in chunk["messages"]:
                                await handler.handle_message(msg)
                elif self._model:
                    from langchain_core.messages import HumanMessage
                    async for chunk in self._model.astream([HumanMessage(content=message)]):
                        await handler.handle_message(chunk)
                
                await handler.finalize()
                await emitter.aemit("__end__", None)

            producer_task = asyncio.create_task(run_agent())

            while True:
                evt = await domain_queue.get()
                evt_type = evt.get("type")
                if evt_type == "__end__":
                    break

                yield make_event(
                    seq=next_seq(),
                    conversation_id=conversation_id,
                    message_id=assistant_message_id,
                    type=evt_type,
                    payload=evt.get("payload", {}),
                )

            await producer_task

        except Exception as e:
            yield make_event(
                seq=next_seq(),
                conversation_id=conversation_id,
                message_id=assistant_message_id,
                type=StreamEventType.ERROR.value,
                payload={"message": str(e)},
            )

    def create_sse_response(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str,
        **kwargs: Any,
    ) -> Any:
        """创建 FastAPI SSE 响应
        
        Args:
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID
            **kwargs: 传递给 chat_stream 的额外参数
        
        Returns:
            FastAPI StreamingResponse
        """
        from langgraph_agent_kit.integrations.fastapi import create_sse_response
        
        event_generator = self.chat_stream(
            message=message,
            conversation_id=conversation_id,
            user_id=user_id,
            **kwargs,
        )
        return create_sse_response(event_generator)
