"""文档业务服务：短 SQL 事务、原文件补偿、版本隔离和 SQL 二次检索校验。"""

import hashlib
from pathlib import PurePath

from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.database import get_db_context
from app.core.embedding import get_embedding_model
from app.models.agent import KnowledgeConfig
from app.models.knowledge_document import (
    Document,
    DocumentChunk,
    DocumentRevision,
    IngestionJob,
    RagSource,
)
from app.services.knowledge.rag.parsing import validate_upload
from app.services.knowledge.rag.settings import (
    RagError,
    collection_name,
    digest,
    embedding_profile,
    processing_profile,
    uid,
)
from app.services.knowledge.rag.storage import DocumentStorage
from app.services.knowledge.rag.vectors import qdrant, scope_filter, validate_vectors

ACTIVE_JOBS = ("queued", "retry_wait", "parsing", "chunking", "embedding", "publishing", "running")


async def source(
    db, config_id: str, managed: bool = True, *, validate_model: bool = True
) -> KnowledgeConfig:
    """校验知识源类型和是否已显式启用托管模式。"""
    if not settings.KNOWLEDGE_RAG_ENABLED:
        raise RagError("托管知识库已停用", 503)
    config = await db.get(KnowledgeConfig, config_id)
    if not config:
        raise RagError("知识源不存在", 404)
    if config.type != "vector":
        raise RagError("仅 vector 知识源支持托管 RAG")
    if managed and not await db.get(RagSource, config_id):
        raise RagError("请先显式启用托管 RAG", 409)
    if (
        validate_model
        and config.embedding_model
        and config.embedding_model != settings.EMBEDDING_MODEL
    ):
        raise RagError("知识源模型与全局 Embedding 配置不一致", 409)
    return config


async def document(
    db, config_id: str, document_id: str, *, allow_deleted: bool = False
) -> Document:
    """从所属知识源读取文档，防止通过其他资源 ID 越界。"""
    doc = await db.get(Document, document_id)
    if not doc or doc.config_id != config_id:
        raise RagError("文档不存在", 404)
    if doc.deleted and not allow_deleted:
        raise RagError("文档已删除", 410)
    return doc


async def revision(db, doc: Document, revision_id: str | None = None) -> DocumentRevision:
    """全文和原文件均要求版本属于目标文章。"""
    rev = await db.get(DocumentRevision, revision_id or doc.current_revision_id or "")
    if not rev or rev.document_id != doc.id:
        raise RagError("版本不存在或尚未发布", 404)
    return rev


async def enable(config_id: str) -> dict:
    """显式切换空知识源，绝不猜测或迁移旧 collection 数据。"""
    async with get_db_context() as db:
        config = await source(db, config_id, managed=False)
        if await db.get(RagSource, config_id):
            return {"config_id": config_id, "rag_enabled": True}
        old_collection = config.collection_name or "knowledge_base"
    async with qdrant() as client:
        if await client.collection_exists(old_collection):
            count = await client.count(old_collection, exact=True)
            if count.count:
                raise RagError("旧 collection 存在数据，请新建知识源或另行迁移", 409)
    async with get_db_context() as db:
        await db.execute(
            update(KnowledgeConfig)
            .where(KnowledgeConfig.id == config_id)
            .values(name=KnowledgeConfig.name)
        )
        await source(db, config_id, managed=False)
        if not await db.get(RagSource, config_id):
            db.add(RagSource(config_id=config_id))
    return {"config_id": config_id, "rag_enabled": True}


def submission(doc: Document, rev: DocumentRevision, job: IngestionJob) -> dict:
    """所有入库入口和重复提交复用相同响应。"""
    return {"document_id": doc.id, "revision_id": rev.id, "job_id": job.id, "status": job.status}


async def enqueue(
    config_id: str,
    data: bytes,
    filename: str,
    mime: str,
    title: str | None,
    *,
    document_id: str | None = None,
    independent: bool = False,
    source_type: str = "file",
    adopt_global_model: bool = False,
) -> dict:
    """先保存原文件，再在序列化短事务中创建版本；失败补偿对象写入。"""
    filename, mime = validate_upload(filename, mime, data)
    profile = processing_profile()
    file_hash = hashlib.sha256(data).hexdigest()
    processing_hash = digest({**profile, "format": PurePath(filename).suffix.lower()})
    rev_id = uid()
    key = f"documents/{config_id}/{rev_id}"
    async with get_db_context() as db:
        await source(db, config_id, validate_model=not adopt_global_model)
        if document_id:
            await document(db, config_id, document_id)
    storage = DocumentStorage()
    await storage.put(key, data, mime)
    retained = False
    try:
        async with get_db_context() as db:
            # 同一知识源内序列化版本号及内容去重；不在此事务中调用网络服务。
            await db.execute(
                update(KnowledgeConfig)
                .where(KnowledgeConfig.id == config_id)
                .values(name=KnowledgeConfig.name)
            )
            config = await source(db, config_id, validate_model=not adopt_global_model)
            if adopt_global_model and config.embedding_model:
                # 显式重建确认使用全局新模型；原索引在全部文章完成重建前仍拒绝混用。
                config.embedding_model = settings.EMBEDDING_MODEL
            if not document_id and not independent:
                from sqlalchemy.orm import aliased

                later = aliased(DocumentRevision)
                no_later_revision = (
                    ~select(later.id)
                    .where(
                        later.document_id == Document.id, later.version > DocumentRevision.version
                    )
                    .exists()
                )
                existing = (
                    await db.execute(
                        select(Document, DocumentRevision, IngestionJob)
                        .join(DocumentRevision, DocumentRevision.document_id == Document.id)
                        .join(IngestionJob, IngestionJob.revision_id == DocumentRevision.id)
                        .where(
                            Document.config_id == config_id,
                            Document.deleted.is_(False),
                            DocumentRevision.file_hash == file_hash,
                            DocumentRevision.processing_hash == processing_hash,
                            IngestionJob.kind == "ingest",
                            no_later_revision,
                        )
                        .order_by(DocumentRevision.created_at.desc())
                        .limit(1)
                    )
                ).first()
                if existing:
                    return submission(*existing)
            if document_id:
                doc = await document(db, config_id, document_id)
                pending = await db.scalar(
                    select(IngestionJob.id).where(
                        IngestionJob.document_id == doc.id, IngestionJob.status.in_(ACTIVE_JOBS)
                    )
                )
                if pending:
                    raise RagError("该文章已有执行中的任务", 409)
                version = 1 + (
                    await db.scalar(
                        select(func.max(DocumentRevision.version)).where(
                            DocumentRevision.document_id == doc.id
                        )
                    )
                    or 0
                )
            else:
                doc = Document(
                    id=uid(), config_id=config_id, title=title or filename, source_type=source_type
                )
                db.add(doc)
                await db.flush()
                version = 1
            rev = DocumentRevision(
                id=rev_id,
                document_id=doc.id,
                version=version,
                object_key=key,
                filename=filename,
                mime_type=mime,
                size=len(data),
                file_hash=file_hash,
                processing_hash=processing_hash,
                profile=profile,
                collection=collection_name(profile["embedding"]),
                chunk_size=profile["chunk_size"],
                chunk_overlap=profile["chunk_overlap"],
            )
            db.add(rev)
            await db.flush()
            job = IngestionJob(id=uid(), document_id=doc.id, revision_id=rev.id)
            db.add(job)
            await db.flush()
            response = submission(doc, rev, job)
        retained = True
        return response
    finally:
        if not retained:
            try:
                # commit 取消/超时的结果可能未知，必须先对账，不能删除已提交版本的原文件。
                async with get_db_context() as db:
                    referenced = await db.scalar(
                        select(DocumentRevision.id)
                        .where(DocumentRevision.object_key == key)
                        .limit(1)
                    )
                if not referenced:
                    await storage.delete(key)
            except Exception:
                # 无法确认提交结果时保留对象；24 小时清理器只删除确定无归属的对象。
                pass


async def reindex(config_id: str, document_id: str) -> dict:
    """复制已保存原文件生成新版本，旧发布版本不被覆盖。"""
    async with get_db_context() as db:
        doc = await document(db, config_id, document_id)
        if doc.current_revision_id:
            rev = await revision(db, doc)
        else:
            rev = await db.scalar(
                select(DocumentRevision)
                .where(DocumentRevision.document_id == doc.id)
                .order_by(DocumentRevision.version.desc())
                .limit(1)
            )
            if not rev:
                raise RagError("文章没有可重建的原文件", 404)
    data = await DocumentStorage().get(rev.object_key)
    return await enqueue(
        config_id,
        data,
        rev.filename,
        rev.mime_type,
        doc.title,
        document_id=document_id,
        adopt_global_model=True,
    )


async def delete_document(config_id: str, document_id: str) -> dict:
    """先关闭检索，再异步清理；并使正在运行的入库任务失去租约。"""
    async with get_db_context() as db:
        await db.execute(
            update(KnowledgeConfig)
            .where(KnowledgeConfig.id == config_id)
            .values(name=KnowledgeConfig.name)
        )
        doc = await document(db, config_id, document_id, allow_deleted=True)
        existing = await db.scalar(
            select(IngestionJob)
            .where(IngestionJob.document_id == doc.id, IngestionJob.kind == "delete")
            .limit(1)
        )
        if existing:
            return {"document_id": doc.id, "job_id": existing.id, "status": existing.status}
        doc.deleted, doc.enabled = True, False
        await db.execute(
            update(IngestionJob)
            .where(IngestionJob.document_id == doc.id, IngestionJob.status.in_(ACTIVE_JOBS))
            .values(status="cancelled", token=None, lease_until=0)
        )
        job = IngestionJob(id=uid(), document_id=doc.id, kind="delete")
        db.add(job)
        await db.flush()
        return {"document_id": doc.id, "job_id": job.id, "status": job.status}


async def search(config_id: str, query: str) -> list[dict]:
    """先向量召回，再用 SQL 当前版本和启停状态排除脏索引。"""
    async with get_db_context() as db:
        config = await source(db, config_id)
        active = (
            await db.scalars(
                select(DocumentRevision)
                .join(Document, Document.current_revision_id == DocumentRevision.id)
                .where(
                    Document.config_id == config_id,
                    Document.enabled.is_(True),
                    Document.deleted.is_(False),
                )
            )
        ).all()
        if not active:
            return []
        profile = embedding_profile()
        if any(r.profile["embedding"] != profile for r in active):
            raise RagError("Embedding 配置已改变，请重建所有已发布文档", 409)
        collection = collection_name(profile)
        top_k, rerank, threshold = config.top_k, config.rerank_enabled, config.similarity_threshold
    vector = await get_embedding_model().aembed_query(query)
    validate_vectors([vector], 1, profile["dimension"])
    wanted = top_k * 3 if rerank else top_k
    output = []
    async with qdrant() as client:
        for limit in sorted({max(32, wanted * n) for n in (1, 3, 10)}):
            from qdrant_client import models

            query_filter = scope_filter(config_id)
            query_filter.must.append(
                models.FieldCondition(
                    key="revision_id", match=models.MatchAny(any=[r.id for r in active])
                )
            )
            hits = (
                await client.query_points(
                    collection_name=collection,
                    query=vector,
                    query_filter=query_filter,
                    limit=limit,
                    score_threshold=threshold,
                    with_payload=True,
                )
            ).points
            ids = [str(h.id) for h in hits]
            if not ids:
                return []
            async with get_db_context() as db:
                rows = (
                    await db.execute(
                        select(DocumentChunk, DocumentRevision, Document)
                        .join(DocumentRevision, DocumentChunk.revision_id == DocumentRevision.id)
                        .join(Document, Document.current_revision_id == DocumentRevision.id)
                        .where(
                            DocumentChunk.id.in_(ids),
                            Document.config_id == config_id,
                            Document.enabled.is_(True),
                            Document.deleted.is_(False),
                        )
                    )
                ).all()
            valid = {c.id: (c, r, d) for c, r, d in rows}
            output = []
            for hit in hits:
                if str(hit.id) not in valid:
                    continue
                c, r, d = valid[str(hit.id)]
                output.append(
                    {
                        "id": c.id,
                        "chunk_id": c.id,
                        "document_id": d.id,
                        "revision_id": r.id,
                        "title": d.title,
                        "content": c.content,
                        "page": c.page,
                        "heading_path": c.heading_path,
                        "start_offset": c.start_offset,
                        "end_offset": c.end_offset,
                        "score": hit.score,
                    }
                )
            if len(output) >= wanted or len(hits) < limit:
                break
    if rerank and output:
        from app.services.knowledge.kb_retriever import KBRetriever

        output = await KBRetriever()._rerank(query, output)
    return output[:top_k]
