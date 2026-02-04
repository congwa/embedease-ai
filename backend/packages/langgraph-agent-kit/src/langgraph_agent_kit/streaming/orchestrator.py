"""基础流编排器"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from langgraph_agent_kit.core.stream_event import StreamEvent
from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.core.emitter import QueueDomainEmitter
from langgraph_agent_kit.core.context import ChatContext
from langgraph_agent_kit.streaming.sse import make_event


class BaseOrchestrator:
    """基础流编排器
    
    将 Agent 产生的 domain events 编排为 StreamEvent 流。
    
    职责：
    - 发出 meta.start（提供服务端 message_id 对齐前端渲染/落库）
    - 转发 assistant.* / tool.* 等事件
    - 管理事件序号和队列
    """

    def __init__(
        self,
        *,
        agent_service: Any,
        conversation_id: str,
        user_id: str,
        user_message: str,
        assistant_message_id: str,
        user_message_id: str | None = None,
        agent_id: str | None = None,
        db: Any = None,
        event_queue_size: int = 10000,
    ):
        self._agent_service = agent_service
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._user_message = user_message
        self._user_message_id = user_message_id
        self._assistant_message_id = assistant_message_id
        self._agent_id = agent_id
        self._db = db
        self._event_queue_size = event_queue_size
        self._seq = 0

    def _next_seq(self) -> int:
        """获取下一个序号"""
        self._seq += 1
        return self._seq

    def _create_context(
        self,
        emitter: QueueDomainEmitter,
    ) -> ChatContext:
        """创建聊天上下文"""
        return ChatContext(
            conversation_id=self._conversation_id,
            user_id=self._user_id,
            assistant_message_id=self._assistant_message_id,
            emitter=emitter,
            db=self._db,
        )

    async def run(self) -> AsyncGenerator[StreamEvent, None]:
        """运行编排流程"""
        # 1) 发送 meta.start
        yield make_event(
            seq=self._next_seq(),
            conversation_id=self._conversation_id,
            message_id=self._assistant_message_id,
            type=StreamEventType.META_START.value,
            payload={
                "user_message_id": self._user_message_id,
                "assistant_message_id": self._assistant_message_id,
            },
        )

        try:
            loop = asyncio.get_running_loop()
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
                maxsize=self._event_queue_size
            )
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)

            context = self._create_context(emitter)

            # 2) 启动 Agent 任务
            producer_task = asyncio.create_task(
                self._agent_service.chat_emit(
                    message=self._user_message,
                    conversation_id=self._conversation_id,
                    user_id=self._user_id,
                    context=context,
                    agent_id=self._agent_id,
                )
            )

            # 3) 消费事件队列
            while True:
                evt = await domain_queue.get()
                evt_type = evt.get("type")
                if evt_type == "__end__":
                    break

                payload = evt.get("payload", {})

                yield make_event(
                    seq=self._next_seq(),
                    conversation_id=self._conversation_id,
                    message_id=self._assistant_message_id,
                    type=evt_type,
                    payload=payload,
                )

            await producer_task

        except Exception as e:
            yield make_event(
                seq=self._next_seq(),
                conversation_id=self._conversation_id,
                message_id=self._assistant_message_id,
                type=StreamEventType.ERROR.value,
                payload={"message": str(e)},
            )
