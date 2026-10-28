"""处理配置快照、稳定身份与可报告的业务错误。"""

import hashlib
import json
import uuid

from app.core.config import settings


class RagError(ValueError):
    """可安全返回客户端的永久业务错误。"""

    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def uid() -> str:
    """为业务资源分配不可预测身份。"""
    return str(uuid.uuid4())


def digest(value: dict) -> str:
    """计算不包含密钥的处理配置指纹。"""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def embedding_profile() -> dict:
    """模型端点也是索引语义的一部分，但不记录 API 密钥。"""
    return {
        "provider": settings.EMBEDDING_PROVIDER,
        "model": settings.EMBEDDING_MODEL,
        "dimension": settings.EMBEDDING_DIMENSION,
        "base_url": settings.effective_embedding_base_url,
    }


def processing_profile() -> dict:
    """在入队时冻结解析、分块及模型配置。"""
    if not 0 <= settings.CHUNK_OVERLAP < settings.CHUNK_SIZE:
        raise RagError("需要 0 <= CHUNK_OVERLAP < CHUNK_SIZE")
    return {
        "embedding": embedding_profile(),
        "parser": "rag-v1",
        "chunk_size": settings.CHUNK_SIZE,
        "chunk_overlap": settings.CHUNK_OVERLAP,
    }


def collection_name(profile: dict) -> str:
    """托管索引与旧知识库、FAQ 和商品集合隔离。"""
    return "kb_managed_v1_" + digest(profile)[:24]
