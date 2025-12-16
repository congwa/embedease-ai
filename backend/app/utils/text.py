"""文本处理工具"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """获取文本分割器"""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "；", "，", " ", ""],
        length_function=len,
    )


def split_text(text: str) -> list[str]:
    """分割长文本"""
    if not text or len(text) <= settings.CHUNK_SIZE:
        return [text] if text else []

    splitter = get_text_splitter()
    return splitter.split_text(text)
