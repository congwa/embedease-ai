"""增强的检索策略 - 混合检索 + 重排序"""

import re

from langchain_core.documents import Document

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rerank import rerank_documents
from app.services.agent.retrieval.catalog import load_products

logger = get_logger("enhanced_retriever")
settings = get_settings()


def extract_keywords(query: str) -> list[str]:
    """从查询中提取关键词

    Args:
        query: 用户查询

    Returns:
        关键词列表
    """
    # 简单的关键词提取（可以使用更复杂的NLP方法）
    # 移除常见的停用词
    stopwords = {
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "怎么",
        "帮我",
        "给我",
        "想要",
        "需要",
        "请",
        "吗",
        "呢",
    }

    # 分词（简单的基于空格和标点符号）
    words = re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", query)
    keywords = [w for w in words if w not in stopwords and len(w) > 1]

    logger.debug("提取关键词", query=query, keywords=keywords)
    return keywords


def filter_by_keywords(
    docs: list[Document], keywords: list[str], min_match: int = 1
) -> list[Document]:
    """根据关键词过滤文档

    Args:
        docs: 文档列表
        keywords: 关键词列表
        min_match: 最少匹配关键词数

    Returns:
        过滤后的文档列表
    """
    if not keywords:
        return docs

    filtered = []
    for doc in docs:
        # 检查文档内容和元数据中的关键词匹配数
        content = doc.page_content.lower()
        product_name = (doc.metadata.get("product_name") or "").lower()
        category = (doc.metadata.get("category") or "").lower()

        combined_text = f"{content} {product_name} {category}"

        match_count = sum(1 for kw in keywords if kw.lower() in combined_text)

        if match_count >= min_match:
            filtered.append(doc)
            logger.debug(
                "关键词匹配",
                product_id=doc.metadata.get("product_id"),
                match_count=match_count,
                keywords_matched=[kw for kw in keywords if kw.lower() in combined_text],
            )

    logger.verbose("关键词过滤完成", original_count=len(docs), filtered_count=len(filtered))
    return filtered


async def rerank_by_relevance(
    docs: list[Document], query: str, keywords: list[str]
) -> list[Document]:
    """基于相关性重排序文档

    使用硅基流动 Rerank API 进行重排序，如果失败则回退到本地打分策略

    Args:
        docs: 文档列表
        query: 原始查询
        keywords: 提取的关键词

    Returns:
        重排序后的文档列表
    """
    if not docs:
        return docs

    # 优先使用 Rerank API
    if settings.RERANK_ENABLED:
        try:
            # 准备文档文本（组合商品名称和描述以获得更好的排序效果）
            doc_texts = []
            for doc in docs:
                product_name = doc.metadata.get("product_name", "")
                category = doc.metadata.get("category", "")
                content = doc.page_content

                # 组合关键信息
                text = f"{product_name} | {category} | {content}"
                doc_texts.append(text)

            # 调用 Rerank API
            logger.debug("使用 Rerank API 进行重排序", query=query, doc_count=len(docs))
            rerank_results = await rerank_documents(
                query=query,
                documents=doc_texts,
                top_n=len(docs),  # 返回所有文档的排序
            )

            # 根据 Rerank 结果重新排序文档
            reranked_docs = []
            for original_idx, relevance_score in rerank_results:
                if 0 <= original_idx < len(docs) and relevance_score >= 0.05:
                    reranked_docs.append(docs[original_idx])

            logger.verbose(
                "Rerank API 重排序完成",
                result_count=len(reranked_docs),
                top_products=[
                    (doc.metadata.get("product_id"), rerank_results[i][1])
                    for i, doc in enumerate(reranked_docs[:5])
                ],
            )

            return reranked_docs

        except Exception as e:
            logger.warning(
                "Rerank API 失败，回退到本地打分策略",
                error=str(e),
            )
            # 继续使用本地打分策略

    # 本地打分策略（后备方案）
    def calculate_relevance_score(doc: Document) -> float:
        """计算文档的相关性分数（本地策略）"""
        score = 0.0

        content = doc.page_content.lower()
        product_name = (doc.metadata.get("product_name") or "").lower()
        category = (doc.metadata.get("category") or "").lower()

        # 1. 关键词匹配度 (权重: 0.4)
        if keywords:
            keyword_matches = sum(1 for kw in keywords if kw.lower() in content)
            name_matches = sum(1 for kw in keywords if kw.lower() in product_name)
            category_matches = sum(1 for kw in keywords if kw.lower() in category)

            keyword_score = (
                keyword_matches * 0.3
                + name_matches * 0.5  # 商品名称匹配权重更高
                + category_matches * 0.2
            ) / max(len(keywords), 1)

            score += keyword_score * 0.4

        # 2. 查询词完整匹配 (权重: 0.3)
        query_lower = query.lower()
        if query_lower in content:
            score += 0.3
        elif query_lower in product_name:
            score += 0.35  # 商品名称完整匹配更重要

        # 3. 内容丰富度 (权重: 0.2)
        content_length_score = min(len(content) / 1000, 1.0)
        score += content_length_score * 0.2

        # 4. 价格合理性 (权重: 0.1)
        # 假设中等价格更受欢迎
        price = doc.metadata.get("price", 0)
        if price:
            # 价格在 500-3000 之间得分较高
            if 500 <= price <= 3000:
                score += 0.1
            elif 100 <= price <= 5000:
                score += 0.05

        return score

    # 计算每个文档的分数并排序
    scored_docs = [(doc, calculate_relevance_score(doc)) for doc in docs]
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    logger.verbose(
        "本地打分重排序完成",
        top_scores=[
            (doc.metadata.get("product_id"), round(score, 3)) for doc, score in scored_docs[:5]
        ],
    )

    return [doc for doc, _ in scored_docs]


def price_bounds(query: str) -> tuple[float | None, float | None]:
    """解析明确的数字预算，不把商品型号或“左右”当成硬价格限制。"""
    interval = re.search(r"(\d+(?:\.\d+)?)\s*(?:元)?\s*[-~～至到]\s*(\d+(?:\.\d+)?)\s*元", query)
    if interval:
        return float(interval[1]), float(interval[2])
    upper = re.search(r"(?:不超过|最多|预算(?:不超过)?|低于)\s*(\d+(?:\.\d+)?)\s*元", query)
    upper = upper or re.search(r"(\d+(?:\.\d+)?)\s*元(?:以内|以下|之内)", query)
    if upper and query[upper.end() :].lstrip().startswith(("左右", "上下", "附近")):
        upper = None
    lower = re.search(r"(?:至少|不低于)\s*(\d+(?:\.\d+)?)\s*元", query)
    return (float(lower[1]) if lower else None, float(upper[1]) if upper else None)


async def enhanced_search(
    query: str,
    k: int = 5,
    enable_keyword_filter: bool = True,
    enable_rerank: bool = True,
    min_price: float | None = None,
    max_price: float | None = None,
    category: str | None = None,
) -> list[Document]:
    """异步召回、SQL 校验、商品聚合后重排；字面关键词不再清空语义候选。"""
    from app.services.agent.retrieval.product import get_retriever_async

    if k <= 0:
        return []
    retriever = await get_retriever_async(k=min(max(k * 6, 30), 200))
    if retriever is None:
        raise RuntimeError("商品检索服务暂时不可用")
    docs = await retriever.ainvoke(query)
    grouped: dict[str, list[Document]] = {}
    for doc in docs:
        pid = doc.metadata.get("product_id")
        if pid:
            grouped.setdefault(str(pid), []).append(doc)
    records = await load_products(list(grouped))
    inferred_min, inferred_max = price_bounds(query)
    lows = [x for x in [min_price, inferred_min] if x is not None]
    highs = [x for x in [max_price, inferred_max] if x is not None]
    low, high = (max(lows) if lows else None), (min(highs) if highs else None)
    if low is not None and high is not None and low > high:
        return []
    candidates = []
    for pid, chunks in grouped.items():
        product = records.get(pid)
        # SQL 删除的商品即使尚有旧向量，也不能再次被推荐。
        if product is None:
            continue
        price = product["price"]
        if (low is not None or high is not None) and price is None:
            continue
        if (low is not None and price < low) or (high is not None and price > high):
            continue
        if category and category not in (product["category"] or ""):
            continue
        excerpts = list(dict.fromkeys(c.page_content for c in chunks))[:2]
        content = (
            f"商品ID: {pid}\n商品名称: {product['name']}\n分类: {product['category']}\n"
            f"价格: {price}\n摘要: {product['summary']}\n匹配资料：\n" + "\n".join(excerpts)
        )
        metadata = {
            **chunks[0].metadata,
            "product_id": pid,
            "product_name": product["name"],
            **{
                key: product[key]
                for key in [
                    "price",
                    "category",
                    "url",
                    "brand",
                    "summary",
                    "specs",
                    "tags",
                    "extra_metadata",
                ]
            },
        }
        candidates.append(Document(page_content=content, metadata=metadata))
    keywords = extract_keywords(query)
    if enable_rerank and candidates:
        candidates = await rerank_by_relevance(candidates, query, keywords)
    return candidates[:k]
