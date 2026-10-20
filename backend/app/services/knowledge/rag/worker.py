"""数据库租约执行器：网络操作不占写事务，只有持有效令牌的执行者可发布。"""

import asyncio
import contextlib
import time

import httpx
from minio.error import S3Error
from openai import APIConnectionError, APIStatusError, APITimeoutError
from qdrant_client import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import OperationalError
from urllib3.exceptions import HTTPError as StorageTransportError

from app.core.database import get_db_context
from app.core.embedding import get_embedding_model
from app.core.logging import get_logger
from app.models.agent import KnowledgeConfig
from app.models.knowledge_document import Document, DocumentChunk, DocumentRevision, IngestionJob
from app.services.knowledge.rag.parsing import make_chunks, parse_document
from app.services.knowledge.rag.service import ACTIVE_JOBS
from app.services.knowledge.rag.settings import RagError, embedding_profile, uid
from app.services.knowledge.rag.storage import DocumentStorage
from app.services.knowledge.rag.vectors import (
    ensure_collection,
    qdrant,
    remove_revision,
    validate_vectors,
)

logger = get_logger("knowledge.worker")
LEASE = 180


class LeaseLost(Exception):
    """任务已被撤销或重新领取，旧执行者必须停止。"""


async def guard(db, job_id: str, token: str, **changes) -> None:
    """CAS 更新同时锁住任务行，保护随后的版本写入。"""
    result = await db.execute(
        update(IngestionJob)
        .where(
            IngestionJob.id == job_id,
            IngestionJob.token == token,
            IngestionJob.lease_until > time.time(),
            IngestionJob.status.in_(ACTIVE_JOBS),
        )
        .values(**changes, lease_until=time.time() + LEASE)
    )
    if result.rowcount != 1:
        raise LeaseLost()


async def stage(job: IngestionJob, status: str, progress: int) -> None:
    """短事务记录阶段，不与 Embedding 或文件读取共用连接。"""
    async with get_db_context() as db:
        await guard(db, job.id, job.token, status=status, progress=progress)
        if job.kind == "ingest":
            await db.execute(
                update(DocumentRevision)
                .where(DocumentRevision.id == job.revision_id)
                .values(status=status, error=None)
            )


async def heartbeat(job: IngestionJob) -> None:
    """长解析和远程调用期间续租，丢失租约时取消整个执行任务。"""
    while True:
        await asyncio.sleep(30)
        async with get_db_context() as db:
            await guard(db, job.id, job.token)


async def claim() -> IngestionJob | None:
    """条件更新领取一个到期任务，支持多实例竞争及过期租约恢复。"""
    now = time.time()
    eligible = (
        IngestionJob.status.in_(ACTIVE_JOBS),
        IngestionJob.available_at <= now,
        or_(IngestionJob.token.is_(None), IngestionJob.lease_until <= now),
    )
    async with get_db_context() as db:
        job_id = await db.scalar(
            select(IngestionJob.id)
            .where(*eligible)
            .order_by(IngestionJob.available_at, IngestionJob.created_at)
            .limit(1)
        )
        if not job_id:
            return None
        token = uid()
        result = await db.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job_id, *eligible)
            .values(token=token, lease_until=now + LEASE, status="running")
        )
        if result.rowcount != 1:
            return None
        return await db.get(IngestionJob, job_id)


async def ingest(job: IngestionJob) -> None:
    """确定性重建分块和向量，全部确认写入后再切换 SQL 当前版本。"""
    async with get_db_context() as db:
        rev = await db.get(DocumentRevision, job.revision_id)
        doc = await db.get(Document, job.document_id)
        if not rev or not doc or doc.deleted:
            raise LeaseLost()
    if rev.profile["embedding"] != embedding_profile():
        raise RagError("任务模型配置已过期，请使用当前配置重新索引")
    await stage(job, "parsing", 5)
    data = await DocumentStorage().get(rev.object_key)
    units = await parse_document(data, rev.filename)
    await stage(job, "chunking", 15)
    full_text, chunks = await asyncio.to_thread(
        make_chunks, units, rev.id, rev.chunk_size, rev.chunk_overlap
    )
    async with get_db_context() as db:
        await guard(db, job.id, job.token)
        await db.execute(delete(DocumentChunk).where(DocumentChunk.revision_id == rev.id))
        db.add_all([DocumentChunk(**chunk) for chunk in chunks])
        await db.execute(
            update(DocumentRevision)
            .where(DocumentRevision.id == rev.id)
            .values(full_text=full_text)
        )
    await stage(job, "embedding", 20)
    async with qdrant() as client:
        await ensure_collection(client, rev.collection, rev.profile["embedding"]["dimension"])
        model = get_embedding_model()
        for offset in range(0, len(chunks), 32):
            batch = chunks[offset : offset + 32]
            vectors = await model.aembed_documents([c["content"] for c in batch])
            validate_vectors(vectors, len(batch), rev.profile["embedding"]["dimension"])
            await stage(job, "embedding", 20 + int(70 * offset / len(chunks)))
            points = [
                models.PointStruct(
                    id=c["id"],
                    vector=v,
                    payload={
                        **c,
                        "config_id": doc.config_id,
                        "document_id": doc.id,
                        "title": doc.title,
                    },
                )
                for c, v in zip(batch, vectors, strict=True)
            ]
            await client.upsert(rev.collection, points=points, wait=True)
        # 确认所有分块存在，不能只凭请求没有抛错发布。
        from app.services.knowledge.rag.vectors import scope_filter

        count = await client.count(
            rev.collection, count_filter=scope_filter(doc.config_id, revision_id=rev.id), exact=True
        )
        if count.count != len(chunks):
            raise RagError("向量索引完整性校验失败")
    await stage(job, "publishing", 95)
    async with get_db_context() as db:
        # 与入队、删除保持同一锁顺序，避免 PostgreSQL 上的相互等待。
        await db.execute(
            update(KnowledgeConfig)
            .where(KnowledgeConfig.id == doc.config_id)
            .values(name=KnowledgeConfig.name)
        )
        await guard(db, job.id, job.token)
        current = await db.get(Document, doc.id)
        if current.deleted:
            raise LeaseLost()
        old = current.current_revision_id
        current.current_revision_id = rev.id
        await db.execute(
            update(DocumentRevision)
            .where(DocumentRevision.id == rev.id)
            .values(status="ready", error=None)
        )
        await db.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job.id)
            .values(status="ready", progress=100, token=None, lease_until=0, error=None)
        )
        if old and old != rev.id:
            db.add(IngestionJob(id=uid(), document_id=doc.id, revision_id=old, kind="prune"))


async def cleanup(job: IngestionJob) -> None:
    """删除外部资源后再清除 SQL 全文；保留版本元信息供重复清理对账。"""
    async with get_db_context() as db:
        doc = await db.get(Document, job.document_id)
        revisions = list(
            (
                await db.scalars(
                    select(DocumentRevision).where(
                        DocumentRevision.document_id == doc.id,
                        *([DocumentRevision.id == job.revision_id] if job.kind == "prune" else []),
                    )
                )
            ).all()
        )
    for rev in revisions:
        await stage(job, "running", 10)
        await remove_revision(rev.collection, doc.config_id, rev.id)
        if job.kind == "delete":
            await DocumentStorage().delete(rev.object_key)
    async with get_db_context() as db:
        await guard(db, job.id, job.token)
        if job.kind == "delete":
            for rev in revisions:
                await db.execute(delete(DocumentChunk).where(DocumentChunk.revision_id == rev.id))
                await db.execute(
                    update(DocumentRevision)
                    .where(DocumentRevision.id == rev.id)
                    .values(full_text=None, status="deleted", error=None)
                )
            await db.execute(
                update(Document)
                .where(Document.id == doc.id)
                .values(cleaned=True, current_revision_id=None)
            )
        await db.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job.id)
            .values(status="ready", progress=100, token=None, lease_until=0, error=None)
        )


def transient(exc: Exception) -> bool:
    """只重试网络、限流和服务端临时错误，格式及配置错误立即失败。"""
    if isinstance(exc, S3Error):
        return exc.code in {"InternalError", "SlowDown", "ServiceUnavailable", "RequestTimeout"}
    if isinstance(exc, APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    if isinstance(exc, UnexpectedResponse):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(
        exc,
        (
            TimeoutError,
            ConnectionError,
            OSError,
            httpx.TransportError,
            APIConnectionError,
            APITimeoutError,
            ResponseHandlingException,
            OperationalError,
            StorageTransportError,
        ),
    )


async def failure(job: IngestionJob, exc: Exception) -> None:
    """保存安全错误信息，清理任务无限退避重试，入库最多自动重试三次。"""
    delay = (10, 30, 120)
    attempts = job.attempts + 1
    retry = job.kind != "ingest" or (transient(exc) and attempts <= len(delay))
    error = str(exc)[:400] if isinstance(exc, RagError) else f"处理失败：{type(exc).__name__}"
    async with get_db_context() as db:
        await guard(db, job.id, job.token)
        status = "retry_wait" if retry else "failed"
        await db.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job.id)
            .values(
                status=status,
                attempts=attempts,
                error=error,
                token=None,
                lease_until=0,
                available_at=time.time() + delay[min(attempts - 1, 2)],
            )
        )
        if job.kind == "ingest":
            await db.execute(
                update(DocumentRevision)
                .where(DocumentRevision.id == job.revision_id)
                .values(status=status, error=error)
            )
    logger.warning("知识库任务失败", job_id=job.id, error=error, retry=retry)


async def run_once() -> bool:
    """执行一个任务；取消时保留租约，到期自动恢复。"""
    job = await claim()
    if not job:
        return False
    operation = asyncio.create_task(ingest(job) if job.kind == "ingest" else cleanup(job))
    renew = asyncio.create_task(heartbeat(job))
    try:
        done, _ = await asyncio.wait({operation, renew}, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            await task
    except LeaseLost:
        pass
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        try:
            await failure(job, exc)
        except LeaseLost:
            pass
    finally:
        for task in (operation, renew):
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError, LeaseLost, Exception):
                await task
    return True


async def sweep_orphans() -> None:
    """删除超过 24 小时且没有版本归属的对象，并对账删除墓碑。"""
    storage = DocumentStorage()
    objects = await storage.objects()
    async with get_db_context() as db:
        referenced = set((await db.scalars(select(DocumentRevision.object_key))).all())
        deleted_ids = list(
            (
                await db.scalars(
                    select(Document.id).where(
                        Document.deleted.is_(True), Document.cleaned.is_(True)
                    )
                )
            ).all()
        )
    cutoff = time.time() - 86400
    for key, modified in objects:
        if modified < cutoff and key not in referenced:
            await storage.delete(key)
    # 删除后仍保留轻量版本元信息，避免超时的旧网络写入留下永久孤儿向量。
    async with get_db_context() as db:
        for doc_id in deleted_ids:
            pending = await db.scalar(
                select(IngestionJob.id).where(
                    IngestionJob.document_id == doc_id,
                    IngestionJob.kind == "delete",
                    IngestionJob.status.in_(ACTIVE_JOBS),
                )
            )
            if not pending:
                db.add(IngestionJob(id=uid(), document_id=doc_id, kind="delete"))
