"""Orchestrator - 可组合的聊天流编排器

使用钩子系统消除各项目重复的编排代码。

最简用法::

    orchestrator = Orchestrator(agent_runner=my_runner)
    async for event in orchestrator.run(message="你好", conversation_id="c1", user_id="u1"):
        yield event

完整用法::

    orchestrator = Orchestrator(
        agent_runner=my_runner,
        hooks=OrchestratorHooks(
            on_stream_start=save_user_message,
            on_event=custom_event_handler,
            on_stream_end=save_assistant_message,
        ),
    )
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from anyio import CancelScope

from langgraph_agent_kit.core.context import ChatContext
from langgraph_agent_kit.core.emitter import QueueDomainEmitter
from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.core.stream_event import StreamEvent
from langgraph_agent_kit.streaming.sse import make_event

# ==================== AgentRunner 协议 ====================


@runtime_checkable
class AgentRunner(Protocol):
    """Agent 运行器协议

    用户需要实现此协议来对接自己的 Agent。
    只需实现一个方法：通过 context.emitter 发送事件。

    示例实现::

        class MyAgentRunner:
            async def run(self, message, context, **kwargs):
                agent = build_my_agent(context.emitter)
                async for chunk in agent.astream({"messages": [...]}):
                    await handler.handle(chunk)
                await context.emitter.aemit("__end__", None)
    """

    async def run(
        self,
        message: str,
        context: ChatContext,
        **kwargs: Any,
    ) -> None:
        """运行 Agent

        通过 context.emitter 发送领域事件。
        运行结束时 **必须** 调用 ``await context.emitter.aemit("__end__", None)``。
        """
        ...


# ==================== ContentAggregator ====================


@dataclass
class ContentAggregator:
    """内容聚合器 - 自动追踪流中的内容

    在 Orchestrator 内部自动维护，用户可在钩子回调中读取聚合结果。

    属性:
        full_content: 累积的助手回复文本
        reasoning: 累积的推理过程文本
        products: 商品数据
        tool_calls: 工具调用追踪 {tool_call_id: {...}}
    """

    full_content: str = ""
    reasoning: str = ""
    products: Any | None = None
    tool_calls: dict[str, dict[str, Any]] = field(default_factory=dict)
    _tool_call_start_times: dict[str, float] = field(default_factory=dict)

    def process_event(self, evt_type: str, payload: dict[str, Any]) -> None:
        """处理单个事件，更新聚合状态"""
        if evt_type == StreamEventType.ASSISTANT_DELTA.value:
            delta = payload.get("delta", "")
            if delta:
                self.full_content += delta

        elif evt_type == StreamEventType.ASSISTANT_REASONING_DELTA.value:
            delta = payload.get("delta", "")
            if delta:
                self.reasoning += delta

        elif evt_type == StreamEventType.ASSISTANT_PRODUCTS.value:
            self.products = payload.get("items")

        elif evt_type == StreamEventType.TOOL_START.value:
            tc_id = payload.get("tool_call_id")
            if tc_id:
                self.tool_calls[tc_id] = {
                    "tool_call_id": tc_id,
                    "name": payload.get("name", "unknown"),
                    "input": payload.get("input", {}),
                    "status": "pending",
                }
                try:
                    loop = asyncio.get_running_loop()
                    self._tool_call_start_times[tc_id] = loop.time()
                except RuntimeError:
                    pass

        elif evt_type == StreamEventType.TOOL_END.value:
            tc_id = payload.get("tool_call_id")
            if tc_id and tc_id in self.tool_calls:
                self.tool_calls[tc_id]["status"] = payload.get("status") or "success"
                self.tool_calls[tc_id]["output"] = payload.get("output_preview")
                if payload.get("error"):
                    self.tool_calls[tc_id]["error_message"] = payload["error"]
                start = self._tool_call_start_times.get(tc_id)
                if start:
                    try:
                        loop = asyncio.get_running_loop()
                        duration_ms = int((loop.time() - start) * 1000)
                        self.tool_calls[tc_id]["duration_ms"] = duration_ms
                    except RuntimeError:
                        pass

        elif evt_type == StreamEventType.ASSISTANT_FINAL.value:
            self.full_content = payload.get("content") or self.full_content
            self.reasoning = payload.get("reasoning") or self.reasoning
            self.products = payload.get("products") or self.products

    @property
    def tool_calls_list(self) -> list[dict[str, Any]]:
        """以列表形式返回所有工具调用"""
        return list(self.tool_calls.values()) if self.tool_calls else []


# ==================== Hook 数据类 ====================


@dataclass
class StreamStartInfo:
    """流开始时的信息，传递给 on_stream_start 钩子"""

    conversation_id: str
    user_id: str
    user_message_id: str
    assistant_message_id: str
    message: str


@dataclass
class StreamEndInfo:
    """流结束时的信息，传递给 on_stream_end 钩子"""

    conversation_id: str
    user_id: str
    assistant_message_id: str
    aggregator: ContentAggregator
    context: ChatContext


@dataclass
class OrchestratorHooks:
    """编排器钩子配置

    所有钩子都是可选的，按需设置。

    属性:
        on_stream_start: 流开始时调用（如保存用户消息）
        on_event: 每个事件到达时调用（如自定义追踪）
        on_stream_end: 流正常结束时调用（如保存助手消息到数据库）
        on_error: 发生异常时调用（如日志记录）
    """

    on_stream_start: Any | None = None
    on_event: Any | None = None
    on_stream_end: Any | None = None
    on_error: Any | None = None


# ==================== Orchestrator ====================


class Orchestrator:
    """可组合的聊天流编排器

    提供：
    - 自动事件队列管理（QueueDomainEmitter + asyncio.Queue）
    - 内置 ContentAggregator（自动追踪 full_content, reasoning, tool_calls）
    - 钩子系统（on_stream_start, on_event, on_stream_end, on_error）
    - 自动 meta.start / error 事件发送

    用法::

        class MyRunner:
            async def run(self, message, context, **kwargs):
                # 你的 Agent 逻辑
                await context.emitter.aemit("__end__", None)

        orchestrator = Orchestrator(
            agent_runner=MyRunner(),
            hooks=OrchestratorHooks(
                on_stream_end=my_save_to_db_func,
            ),
        )

        # 在 FastAPI 路由中使用
        async for event in orchestrator.run(message="你好", ...):
            yield event
    """

    def __init__(
        self,
        *,
        agent_runner: AgentRunner,
        hooks: OrchestratorHooks | None = None,
        event_queue_size: int = 10000,
    ):
        """初始化编排器

        Args:
            agent_runner: Agent 运行器实例（需实现 AgentRunner 协议）
            hooks: 钩子配置
            event_queue_size: 事件队列最大容量
        """
        self._agent_runner = agent_runner
        self._hooks = hooks or OrchestratorHooks()
        self._event_queue_size = event_queue_size

    async def run(
        self,
        *,
        message: str,
        conversation_id: str,
        user_id: str,
        assistant_message_id: str | None = None,
        user_message_id: str | None = None,
        db: Any = None,
        **runner_kwargs: Any,
    ) -> AsyncGenerator[StreamEvent, None]:
        """运行编排流程

        Args:
            message: 用户消息
            conversation_id: 会话 ID
            user_id: 用户 ID
            assistant_message_id: 助手消息 ID（可选，自动生成）
            user_message_id: 用户消息 ID（可选，自动生成）
            db: 数据库会话（可选，传入 ChatContext）
            **runner_kwargs: 传递给 agent_runner.run() 的额外参数

        Yields:
            StreamEvent
        """
        if assistant_message_id is None:
            assistant_message_id = str(uuid.uuid4())
        if user_message_id is None:
            user_message_id = str(uuid.uuid4())

        seq = 0

        def next_seq() -> int:
            nonlocal seq
            seq += 1
            return seq

        # 流开始钩子
        start_info = StreamStartInfo(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            message=message,
        )
        if self._hooks.on_stream_start:
            await self._hooks.on_stream_start(start_info)

        # meta.start 事件
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

        aggregator = ContentAggregator()
        producer_task: asyncio.Task | None = None

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
                db=db,
            )

            # 启动 Agent 任务
            producer_task = asyncio.create_task(
                self._agent_runner.run(
                    message=message,
                    context=context,
                    **runner_kwargs,
                )
            )

            # 消费事件队列
            while True:
                evt = await domain_queue.get()
                evt_type = evt.get("type")
                if evt_type == "__end__":
                    break

                payload = evt.get("payload", {})

                # 聚合
                aggregator.process_event(evt_type, payload)

                # 事件钩子
                if self._hooks.on_event:
                    await self._hooks.on_event(evt_type, payload, aggregator)

                # yield StreamEvent
                yield make_event(
                    seq=next_seq(),
                    conversation_id=conversation_id,
                    message_id=assistant_message_id,
                    type=evt_type,
                    payload=payload,
                )

            await producer_task

            # 流结束钩子
            end_info = StreamEndInfo(
                conversation_id=conversation_id,
                user_id=user_id,
                assistant_message_id=assistant_message_id,
                aggregator=aggregator,
                context=context,
            )
            if self._hooks.on_stream_end:
                await self._hooks.on_stream_end(end_info)

        except Exception as e:
            # 错误钩子
            if self._hooks.on_error:
                await self._hooks.on_error(e, conversation_id)

            yield make_event(
                seq=next_seq(),
                conversation_id=conversation_id,
                message_id=assistant_message_id,
                type=StreamEventType.ERROR.value,
                payload={"message": str(e)},
            )

        finally:
            # 客户端断线或调用方关闭生成器时，同步停止真正运行中的 Agent。
            if producer_task is not None:
                if not producer_task.done():
                    producer_task.cancel()
                with CancelScope(shield=True):
                    await asyncio.gather(producer_task, return_exceptions=True)

    def create_sse_response(self, **kwargs: Any) -> Any:
        """创建 FastAPI SSE 响应

        Args:
            **kwargs: 传递给 run() 的所有参数

        Returns:
            FastAPI StreamingResponse
        """
        from langgraph_agent_kit.integrations.fastapi import create_sse_response

        return create_sse_response(self.run(**kwargs))
