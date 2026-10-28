"""业务扩展响应处理器

继承 SDK 的 StreamingResponseHandler，添加商品数据处理逻辑。
"""

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import ToolMessage
from langgraph_agent_kit import StreamEventType, StreamingResponseHandler

from app.core.logging import get_logger

logger = get_logger("streams.business_handler")


def normalize_products_payload(payload: Any) -> list[dict[str, Any]] | None:
    """标准化商品数据格式

    Args:
        payload: 原始商品数据（可能是 dict 或 list）

    Returns:
        标准化后的商品列表，或 None
    """
    if payload is None:
        return None

    candidate: Any = payload
    if (
        isinstance(candidate, dict)
        and "products" in candidate
        and isinstance(candidate.get("products"), list)
    ):
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


@dataclass
class BusinessResponseHandler(StreamingResponseHandler):
    """业务扩展响应处理器
    
    继承 SDK 的 StreamingResponseHandler，添加：
    - 商品数据提取和聚合
    - ASSISTANT_PRODUCTS 事件推送
    """

    # 本轮上下文供最终引用校验，不能从模型生成的链接创建来源。
    context: Any = None

    # 商品数据
    products_data: list[dict[str, Any]] | None = field(default=None, init=False)

    async def _handle_tool_message(self, msg: ToolMessage) -> None:
        """处理工具消息，提取商品数据"""
        # 调用父类去重逻辑
        await super()._handle_tool_message(msg)

        content = msg.content
        try:
            parsed_data: Any
            if isinstance(content, str):
                parsed_data = json.loads(content)
            elif isinstance(content, (list, dict)):
                parsed_data = content
            else:
                return

            normalized_products = normalize_products_payload(parsed_data)
            if normalized_products is None:
                return

            # 收集商品数据，延迟到 finalize 阶段统一推送
            if self.products_data is None:
                self.products_data = normalized_products
            else:
                # 合并多次工具调用返回的商品（去重）
                seen_ids = {p.get("id") for p in self.products_data}
                for product in normalized_products:
                    if product.get("id") not in seen_ids:
                        self.products_data.append(product)
                        seen_ids.add(product.get("id"))
        except Exception:
            pass

    async def finalize(self) -> dict[str, Any]:
        """发送最终事件，返回汇总数据"""
        # 引用先登记后发出，保证客户端收到 URL 时即可读取原文。
        from app.services.knowledge.rag.citations import finalize_citations
        citation_content = self.full_content
        if self.content_events == 0 and self.full_reasoning.strip():
            citation_content = self.full_reasoning
        citations = await finalize_citations(self.context, citation_content)
        if citations:
            await self.emitter.aemit("assistant.citations", {"items": citations})

        # 在总结阶段统一推送商品数据
        if self.products_data:
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_PRODUCTS.value,
                {"items": self.products_data},
            )
            logger.info(
                "📦 推送商品推荐（总结阶段）",
                conversation_id=self.conversation_id,
                product_count=len(self.products_data),
            )

        # 调用父类 finalize
        result = await super().finalize()

        # 添加商品数据到结果
        result["products"] = (
            self.products_data
            if isinstance(self.products_data, list) or self.products_data is None
            else [self.products_data]
        )

        result["citations"] = citations
        return result
