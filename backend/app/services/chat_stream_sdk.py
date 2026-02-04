"""聊天流编排层 - SDK 版本

使用 langgraph-agent-kit SDK 重构的实现。
与旧版本 API 兼容，可通过配置切换。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from langgraph_agent_kit import (
    StreamEvent,
    StreamEventType,
    QueueDomainEmitter,
    make_event,
)
from langgraph_agent_kit.core.context import ChatContext

from app.core.logging import get_logger
from app.services.conversation import ConversationService

logger = get_logger("chat_stream_sdk")


class ChatStreamOrchestratorSDK:
    """SDK 版本的聊天流编排器
    
    继承 SDK 设计理念，添加业务特定逻辑：
    - 数据库消息保存
    - 工具调用追踪
    - 商品数据聚合
    
    与 Legacy 版本保持完全相同的接口签名。
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
        agent_id: str | None = None,
        images: list[Any] | None = None,
        db: Any = None,
    ) -> None:
        self._conversation_service = conversation_service
        self._agent_service = agent_service
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._user_message = user_message
        self._user_message_id = user_message_id
        self._assistant_message_id = assistant_message_id
        self._agent_id = agent_id
        self._images = images
        self._db = db

        self._seq = 0
        self._full_content = ""
        self._reasoning = ""
        self._products: Any | None = None

        self._tool_calls: dict[str, dict[str, Any]] = {}
        self._tool_call_start_times: dict[str, float] = {}

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def run(self) -> AsyncGenerator[StreamEvent, None]:
        """运行编排流程（与旧版本 API 兼容）"""
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
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10000)
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)

            chat_context = ChatContext(
                conversation_id=self._conversation_id,
                user_id=self._user_id,
                assistant_message_id=self._assistant_message_id,
                emitter=emitter,
                db=self._db,
            )

            producer_task = asyncio.create_task(
                self._agent_service.chat_emit(
                    message=self._user_message,
                    conversation_id=self._conversation_id,
                    user_id=self._user_id,
                    context=chat_context,
                    agent_id=self._agent_id,
                )
            )

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

                elif evt_type == StreamEventType.TOOL_START.value:
                    tc_id = payload.get("tool_call_id")
                    if tc_id:
                        self._tool_calls[tc_id] = {
                            "tool_call_id": tc_id,
                            "name": payload.get("name", "unknown"),
                            "input": payload.get("input", {}),
                            "status": "pending",
                        }
                        self._tool_call_start_times[tc_id] = loop.time()

                elif evt_type == StreamEventType.TOOL_END.value:
                    tc_id = payload.get("tool_call_id")
                    tool_status = payload.get("status")
                    if tc_id and tc_id in self._tool_calls:
                        self._tool_calls[tc_id]["status"] = tool_status or "success"
                        self._tool_calls[tc_id]["output"] = payload.get("output_preview")
                        if payload.get("error"):
                            self._tool_calls[tc_id]["error_message"] = payload.get("error")
                        start_time = self._tool_call_start_times.get(tc_id)
                        if start_time:
                            duration_ms = int((loop.time() - start_time) * 1000)
                            self._tool_calls[tc_id]["duration_ms"] = duration_ms

                elif evt_type == StreamEventType.ASSISTANT_FINAL.value:
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

            # 2) 落库
            products_json = None
            if self._products is not None:
                products_json = json.dumps(self._products, ensure_ascii=False)

            tool_calls_data = list(self._tool_calls.values()) if self._tool_calls else None

            extra_metadata: dict[str, Any] = {}
            if self._reasoning:
                extra_metadata["reasoning"] = self._reasoning
            if tool_calls_data:
                extra_metadata["tool_calls_summary"] = [
                    {"name": tc.get("name"), "status": tc.get("status")}
                    for tc in tool_calls_data
                ]

            latency_ms = chat_context.response_latency_ms

            await self._conversation_service.add_message(
                conversation_id=self._conversation_id,
                role="assistant",
                content=self._full_content,
                products=products_json,
                message_id=self._assistant_message_id,
                extra_metadata=extra_metadata if extra_metadata else None,
                tool_calls_data=tool_calls_data,
                latency_ms=latency_ms,
            )
            logger.debug(
                "已保存完整 assistant message (SDK)",
                message_id=self._assistant_message_id,
                content_length=len(self._full_content),
                tool_call_count=len(tool_calls_data) if tool_calls_data else 0,
            )

        except Exception as e:
            logger.exception(
                "聊天流编排失败 (SDK)",
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
