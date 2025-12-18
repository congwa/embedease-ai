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
        mode: str = "natural",
    ) -> None:
        self._conversation_service = conversation_service
        self._agent_service = agent_service
        self._conversation_id = conversation_id
        self._user_id = user_id
        self._user_message = user_message
        self._user_message_id = user_message_id
        self._assistant_message_id = assistant_message_id
        self._mode = mode

        self._seq = 0
        self._full_content = ""
        self._reasoning = ""
        self._products: Any | None = None
        self._saw_tool_end = False  # strict 模式兜底检查用
        self._last_tool_end_status: str | None = None
        self._last_tool_end_name: str | None = None

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
                mode=self._mode,
                emitter=emitter,
            )

            # Agent 只负责把 domain events 写入 emitter；Orchestrator 是唯一对外 SSE 出口
            producer_task = asyncio.create_task(
                self._agent_service.chat_emit(
                    message=self._user_message,
                    conversation_id=self._conversation_id,
                    user_id=self._user_id,
                    context=chat_context,
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

                elif evt_type == StreamEventType.TOOL_END.value:
                    self._saw_tool_end = True
                    tool_name = payload.get("name")
                    tool_status = payload.get("status")
                    self._last_tool_end_name = tool_name if isinstance(tool_name, str) else self._last_tool_end_name
                    self._last_tool_end_status = (
                        tool_status if isinstance(tool_status, str) else self._last_tool_end_status
                    )

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

            # strict 模式兜底：如果没有 tool.end 事件，说明模型没有调用工具
            # strict 模式兜底：作为最终保险，仅在“没有任何可展示内容且没有 products”时触发
            if self._mode == "strict" and not (self._full_content or "").strip() and self._products is None:
                if not self._saw_tool_end:
                    fallback_msg = (
                        "**严格模式提示**\n\n"
                        "为了确保回答有据可依，我需要先通过工具获取数据。\n\n"
                        "当前这轮对话我没有检测到任何工具调用，因此无法给出可靠的推荐。\n\n"
                        "请补充：预算范围、品类/关键词、使用场景、核心偏好（1-2点）。"
                    )
                    logger.warning(
                        "strict 兜底：未检测到工具调用，输出引导信息",
                        conversation_id=self._conversation_id,
                    )
                    self._full_content = fallback_msg

                elif self._last_tool_end_status == "empty":
                    fallback_msg = (
                        "**严格模式提示（无结果）**\n\n"
                        "我已尝试通过工具检索，但当前商品库没有命中与你描述匹配的结果。\n\n"
                        "你可以这样提高命中率：\n"
                        "1. 提供 **品类 + 1-2 个关键词**（例如：‘降噪耳机 轻便’）\n"
                        "2. 给出 **预算范围/价格上限**\n"
                        "3. 说明 **使用场景**（通勤/运动/办公/游戏）\n"
                        "4. 如果你有候选商品名/型号，也可以直接发我，我会走详情/对比来分析"
                    )
                    logger.warning(
                        "strict 兜底：工具返回 empty，输出无结果引导",
                        conversation_id=self._conversation_id,
                        tool_name=self._last_tool_end_name,
                    )
                    self._full_content = fallback_msg

                elif self._last_tool_end_status == "error":
                    fallback_msg = (
                        "**严格模式提示（工具出错）**\n\n"
                        "我在通过工具获取商品数据时遇到了问题，暂时无法保证推荐的可靠性。\n\n"
                        "你可以：\n"
                        "1. 稍后重试\n"
                        "2. 简化需求（只给品类 + 关键词 + 预算）我会重新检索\n"
                        "3. 如果你有商品名/型号，直接发我，我可以优先走详情/对比"
                    )
                    logger.warning(
                        "strict 兜底：工具返回 error，输出出错引导",
                        conversation_id=self._conversation_id,
                        tool_name=self._last_tool_end_name,
                    )
                    self._full_content = fallback_msg

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
