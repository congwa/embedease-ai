"""管理入口密钥与引用链接签名；不把管理密钥发送给浏览器。"""

import base64
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import quote

from fastapi import Header

from app.core.config import settings
from app.services.knowledge.rag.settings import RagError


def require_admin_key(value: str | None) -> None:
    """配置缺失时关闭入口；常量时间比较避免泄露密钥内容。"""
    if not settings.KNOWLEDGE_RAG_ENABLED:
        raise RagError("托管知识库已停用", 503)
    if not settings.KNOWLEDGE_ADMIN_KEY:
        raise RagError("知识库管理密钥未配置", 503)
    if not value or not hmac.compare_digest(value, settings.KNOWLEDGE_ADMIN_KEY):
        raise RagError("知识库管理密钥无效", 401)


async def admin_access(x_knowledge_admin_key: str | None = Header(default=None)) -> None:
    """仅管理路由依赖此鉴权，不改变既有聊天协议。"""
    require_admin_key(x_knowledge_admin_key)


def signing_key() -> bytes:
    """独立签名密钥优先，管理密钥回退；均不允许空值。"""
    key = settings.KNOWLEDGE_SIGNING_KEY or settings.KNOWLEDGE_ADMIN_KEY
    if len(key) < 32:
        raise RagError("知识库签名密钥或管理密钥需要至少 32 个字符", 503)
    return key.encode()


def token_for(citation) -> str:
    """凭证只绑定服务器已登记的消息与段落，不接受客户端指定资源。"""
    payload = {
        "c": citation.conversation_id,
        "m": citation.message_id,
        "i": citation.id,
        "r": citation.revision_id,
        "exp": int(time.time()) + settings.KNOWLEDGE_CITATION_TTL,
    }
    raw = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    signature = hmac.new(signing_key(), raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + signature


def verify_token(token: str) -> dict:
    """严格校验长度、签名及到期时间，失败统一拒绝。"""
    try:
        if len(token) > 2048:
            raise ValueError()
        raw, signature = token.split(".")
        expected = hmac.new(signing_key(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if payload["exp"] <= time.time():
            raise ValueError()
        return payload
    except (ValueError, KeyError, TypeError) as exc:
        raise RagError("引用访问凭证无效或已过期", 401) from exc


def source_url(citation) -> str:
    """相对地址便于前端和嵌入端使用各自 API base URL。"""
    return f"/api/v1/knowledge/citations/{citation.id}?token={quote(token_for(citation))}"


class CitationAccessLogFilter(logging.Filter):
    """脱敏 Uvicorn 访问日志中的引用凭证；网关也必须配置同等脱敏。"""

    def filter(self, record: logging.LogRecord) -> bool:
        """只改写日志参数副本，不更改实际 HTTP 请求。"""
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            args = list(record.args)
            path = args[2]
            if isinstance(path, str) and "/knowledge/citations/" in path and "?" in path:
                args[2] = path.split("?", 1)[0] + "?redacted"
                record.args = tuple(args)
        return True
