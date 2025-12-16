"""聊天流编排层：聚合业务事件、落库、输出统一协议事件。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.schemas.stream import StreamEvent
from app.services.conversation import ConversationService
from app.services.streaming.context import ChatContext
from app.services.streaming.emitter import QueueDomainEmitter
from app.services.streaming.sse import make_event

logger = get_logger("chat_stream")


class ChatStreamOrchestrator:
    """将 Agent 产生的 domain events 编排为 StreamEvent 流。

    职责：
    - 发出 meta.start（提供服务端 message_id 对齐前端渲染/落库）
    - 转发 assistant.* / tool.* 等事件
    - 聚合流式增量，最终落库 assistant 消息（保证 message_id 一致）
    """

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        agent_service: Any,
        conversation_id: str,
        user_id: str,
        user_message: str,
        user_message_id: str,
        assistant_message_id: str,
    ) -> None:
        self._conversation_service = conversation_service
        self._agent_service = agent_service
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._user_message = user_message
        self._user_message_id = user_message_id
        self._assistant_message_id = assistant_message_id

        self._seq = 0
        self._full_content = ""
        self._reasoning = ""
        self._products: Any | None = None

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def run(self) -> AsyncGenerator[StreamEvent, None]:
        # 1) start
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
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)

            chat_context = ChatContext(
                conversation_id=self._conversation_id,
                user_id=self._user_id,
                assistant_message_id=self._assistant_message_id,
                emitter=emitter,
            )

            async def _produce_agent_events() -> None:
                try:
                    async for evt in self._agent_service.chat(
                        message=self._user_message,
                        conversation_id=self._conversation_id,
                        user_id=self._user_id,
                        context=chat_context,
                    ):
                        await domain_queue.put(evt)
                except Exception as e:
                    await domain_queue.put(
                        {"type": StreamEventType.ERROR.value, "payload": {"message": str(e)}}
                    )
                finally:
                    await domain_queue.put({"type": "__end__", "payload": None})

            producer_task = asyncio.create_task(_produce_agent_events())

            while True:
                evt = await domain_queue.get()
                evt_type = evt.get("type")
                if evt_type == "__end__":
                    break

                payload = evt.get("payload", {})

                if evt_type == StreamEventType.ASSISTANT_DELTA.value:
                    delta = payload.get("delta", "")
                    if delta:
                        self._full_content += delta

                elif evt_type == StreamEventType.ASSISTANT_REASONING_DELTA.value:
                    delta = payload.get("delta", "")
                    if delta:
                        self._reasoning += delta

                elif evt_type == StreamEventType.ASSISTANT_PRODUCTS.value:
                    self._products = payload.get("items")

                elif evt_type == StreamEventType.ASSISTANT_FINAL.value:
                    # 以 final 为准，对齐最终状态
                    self._full_content = payload.get("content") or self._full_content
                    self._reasoning = payload.get("reasoning") or self._reasoning
                    self._products = payload.get("products") or self._products

                yield make_event(
                    seq=self._next_seq(),
                    conversation_id=self._conversation_id,
                    message_id=self._assistant_message_id,
                    type=evt_type,
                    payload=payload,
                )

            await producer_task

            # 2) 落库（仅在正常完成时保存）
            products_json = None
            if self._products is not None:
                products_json = json.dumps(self._products, ensure_ascii=False)

            await self._conversation_service.add_message(
                conversation_id=self._conversation_id,
                role="assistant",
                content=self._full_content,
                products=products_json,
                message_id=self._assistant_message_id,
            )
            logger.debug(
                "已保存完整 assistant message",
                message_id=self._assistant_message_id,
                content_length=len(self._full_content),
            )

        except Exception as e:
            logger.exception(
                "聊天流编排失败",
                conversation_id=self._conversation_id,
                error=str(e),
            )
            yield make_event(
                seq=self._next_seq(),
                conversation_id=self._conversation_id,
                message_id=self._assistant_message_id,
                type=StreamEventType.ERROR.value,
                payload={"message": str(e)},
            )
