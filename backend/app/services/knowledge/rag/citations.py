"""只为本轮实际引用的已检索段落生成凭证，并保留可重新签名的历史快照。"""

import re
import uuid

from sqlalchemy import select

from app.core.database import get_db_context
from app.models.knowledge_document import Document, MessageCitation
from app.services.knowledge.rag.security import signing_key, source_url
from app.services.knowledge.rag.settings import RagError


def citation_view(row: MessageCitation, doc: Document | None) -> dict:
    """业务只展示最新原文，文章更新后清空旧摘要和旧坐标，避免误定位。"""
    item = dict(row.snapshot)
    updated = bool(doc and doc.current_revision_id != row.revision_id)
    item["source_updated"] = updated
    item["deleted"] = not doc or doc.deleted
    if updated and not item["deleted"]:
        item.update(
            revision_id=doc.current_revision_id,
            title=doc.title,
            chunk_id=None,
            excerpt=None,
            page=None,
            heading_path=[],
            start_offset=None,
            end_offset=None,
            notice="原文已更新，当前展示最新内容；此历史回答可能已过时。",
        )
    return item


async def finalize_citations(context, content: str) -> list[dict]:
    """模型标记必须匹配本轮 registry，模型不能自行创造可访问来源。"""
    registry = getattr(context, "rag_sources", {}) if context else {}
    if not registry:
        return []
    used = set(re.findall(r"\[(S[1-9]\d*)\]", content))
    selected = [item for item in registry.values() if item["label"] in used]
    if not selected:
        return []
    signing_key()
    result = []
    async with get_db_context() as db:
        for item in selected:
            # 停用允许历史阅读；删除不应在最终时签发新的来源链接。
            doc = await db.get(Document, item["document_id"])
            if not doc or doc.deleted:
                continue
            cid = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{context.assistant_message_id}:{item['chunk_id']}")
            )
            snapshot = {
                key: value
                for key, value in item.items()
                if key not in {"content", "score", "id", "source_url"}
            }
            snapshot.update(citation_id=cid, excerpt=item["content"][:240])
            row = await db.get(MessageCitation, cid)
            if row is None:
                row = MessageCitation(
                    id=cid,
                    conversation_id=context.conversation_id,
                    message_id=context.assistant_message_id,
                    document_id=item["document_id"],
                    revision_id=item["revision_id"],
                    chunk_id=item["chunk_id"],
                    snapshot=snapshot,
                )
                db.add(row)
            result.append({**citation_view(row, doc), "source_url": source_url(row)})
    return result


def stable_citations(items: list[dict]) -> list[dict]:
    """持久化稳定身份和摘要，避免保存很快过期的访问凭证。"""
    return [{k: v for k, v in item.items() if k != "source_url"} for item in items]


async def history_metadata(db, message) -> dict | None:
    """按现有历史读取权限重新签发 URL，不以请求传入的引用作为依据。"""
    metadata = dict(message.extra_metadata or {})
    if not metadata.get("citations"):
        return metadata or None
    rows = (
        await db.scalars(
            select(MessageCitation).where(
                MessageCitation.message_id == message.id,
                MessageCitation.conversation_id == message.conversation_id,
            )
        )
    ).all()
    result = []
    for row in rows:
        doc = await db.get(Document, row.document_id)
        item = citation_view(row, doc)
        if not item["deleted"]:
            try:
                item["source_url"] = source_url(row)
            except RagError:
                item["source_url"] = None
        result.append(item)
    metadata["citations"] = result
    return metadata
