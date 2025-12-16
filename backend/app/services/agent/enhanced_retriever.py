"""增强的检索策略 - 混合检索 + 重排序"""

import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rerank import rerank_documents
from app.services.agent.retriever import get_retriever

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
                f"关键词匹配",
                product_id=doc.metadata.get("product_id"),
                match_count=match_count,
                keywords_matched=[kw for kw in keywords if kw.lower() in combined_text],
            )

    logger.info(f"关键词过滤完成", original_count=len(docs), filtered_count=len(filtered))
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
    if settings.SILICONFLOW_RERANK_ENABLED:
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
                if original_idx < len(docs):
                    reranked_docs.append(docs[original_idx])

            logger.info(
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

    logger.info(
        "本地打分重排序完成",
        top_scores=[
            (doc.metadata.get("product_id"), round(score, 3)) for doc, score in scored_docs[:5]
        ],
    )

    return [doc for doc, _ in scored_docs]


async def enhanced_search(
    query: str, k: int = 5, enable_keyword_filter: bool = True, enable_rerank: bool = True
) -> list[Document]:
    """增强的商品搜索

    结合向量相似度、关键词过滤和重排序的混合检索策略

    Args:
        query: 搜索查询
        k: 返回结果数量
        enable_keyword_filter: 是否启用关键词过滤
        enable_rerank: 是否启用重排序

    Returns:
        搜索结果文档列表
    """
    logger.info(
        "开始增强检索",
        query=query,
        k=k,
        keyword_filter=enable_keyword_filter,
        rerank=enable_rerank,
    )

    # 1. 向量相似度检索（检索更多结果以供后续过滤）
    retriever = get_retriever(k=k * 2)
    docs = retriever.invoke(query)

    if not docs:
        logger.warning("向量检索无结果")
        return []

    logger.info(f"向量检索完成", doc_count=len(docs))

    # 2. 提取关键词
    keywords = extract_keywords(query)

    # 3. 关键词过滤
    if enable_keyword_filter and keywords:
        docs = filter_by_keywords(docs, keywords, min_match=1)

    if not docs:
        logger.warning("关键词过滤后无结果")
        return []

    # 4. 重排序
    if enable_rerank:
        docs = await rerank_by_relevance(docs, query, keywords)

    # 5. 返回前 k 个结果
    result = docs[:k]

    logger.info(
        "增强检索完成",
        final_count=len(result),
        product_ids=[doc.metadata.get("product_id") for doc in result],
    )

    return result


def get_enhanced_retriever(k: int = 5) -> VectorStoreRetriever:
    """获取增强的检索器（保持接口兼容性）

    Args:
        k: 返回结果数量

    Returns:
        增强的检索器
    """
    # 注意：这里返回的是标准检索器，实际增强逻辑在 enhanced_search 函数中
    # 如果需要在工具中使用增强检索，应该直接调用 enhanced_search 函数
    return get_retriever(k=k)
