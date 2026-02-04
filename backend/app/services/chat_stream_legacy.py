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
        agent_id: str | None = None,
        images: list[Any] | None = None,
        db: Any = None,  # 数据库会话（传递给 ChatContext，供工具使用）
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

        # 工具调用追踪：收集 tool.start/tool.end 事件中的信息
        self._tool_calls: dict[str, dict[str, Any]] = {}  # tool_call_id -> tool_call_data
        self._tool_call_start_times: dict[str, float] = {}  # tool_call_id -> start_time

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
            # 逐字推理会产生大量事件；队列容量适当加大，避免频繁 backpressure/丢弃
            domain_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=10000)
            emitter = QueueDomainEmitter(queue=domain_queue, loop=loop)

            chat_context = ChatContext(
                conversation_id=self._conversation_id,
                user_id=self._user_id,
                assistant_message_id=self._assistant_message_id,
                emitter=emitter,
                db=self._db,
            )

            # Agent 只负责把 domain events 写入 emitter；Orchestrator 是唯一对外 SSE 出口
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
                    # 记录工具调用开始
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
                    # 更新工具调用结果
                    tc_id = payload.get("tool_call_id")
                    tool_status = payload.get("status")
                    if tc_id and tc_id in self._tool_calls:
                        self._tool_calls[tc_id]["status"] = tool_status or "success"
                        self._tool_calls[tc_id]["output"] = payload.get("output_preview")
                        if payload.get("error"):
                            self._tool_calls[tc_id]["error_message"] = payload.get("error")
                        # 计算耗时
                        start_time = self._tool_call_start_times.get(tc_id)
                        if start_time:
                            duration_ms = int((loop.time() - start_time) * 1000)
                            self._tool_calls[tc_id]["duration_ms"] = duration_ms

                elif evt_type == StreamEventType.ASSISTANT_FINAL.value:
                    # 以 final 为准，对齐最终状态
                    self._full_content = payload.get("content") or self._full_content
                    self._reasoning = payload.get("reasoning") or self._reasoning
                    self._products = payload.get("products") or self._products
                # logger.debug(
                #     "处理事件",
                #     evt_type=evt_type,
                #     payload=payload,
                # )
                yield make_event(
                    seq=self._next_seq(),
                    conversation_id=self._conversation_id,
                    message_id=self._assistant_message_id,
                    type=evt_type,
                    payload=payload,
                )

            # 等待 producer 结束（如遇异常，chat_emit 会通过 error event 发给前端）
            await producer_task

            # 2) 落库（仅在正常完成时保存）
            products_json = None
            if self._products is not None:
                products_json = json.dumps(self._products, ensure_ascii=False)

            # 构建工具调用数据列表
            tool_calls_data = list(self._tool_calls.values()) if self._tool_calls else None

            # 构建 extra_metadata（含工具调用、推理等信息）
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
                "已保存完整 assistant message",
                message_id=self._assistant_message_id,
                content_length=len(self._full_content),
                tool_call_count=len(tool_calls_data) if tool_calls_data else 0,
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
