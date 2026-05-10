"""增强检索关键词提取与过滤"""

from langchain_core.documents import Document

from app.services.agent.retrieval.enhanced import extract_keywords, filter_by_keywords


def test_extract_keywords_chinese_sentence_includes_bigrams():
    """长中文无空格时应拆出二字片段，便于匹配「深度保洁」等名称"""
    kws = extract_keywords("平台上的保洁服务")
    assert "保洁" in kws, kws
    assert "服务" in kws, kws


def test_filter_by_keywords_matches_substring_in_product_name():
    """关键词为「保洁」时应命中名称含保洁的商品文档"""
    doc = Document(
        page_content="含厨房油污、卫生间除垢",
        metadata={
            "product_id": "HS0001",
            "product_name": "全屋深度保洁 4 小时",
            "category": "家庭保洁",
        },
    )
    out = filter_by_keywords([doc], ["保洁"], min_match=1)
    assert len(out) == 1

