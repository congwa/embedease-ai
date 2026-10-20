"""托管 RAG 管理 API 与签名引用 API；原文件只通过后端读取。"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.database import get_db_context
from app.models.agent import KnowledgeConfig
from app.models.knowledge_document import (
    Document,
    DocumentChunk,
    DocumentRevision,
    IngestionJob,
    MessageCitation,
)
from app.schemas.knowledge_document import (
    ContentResponse,
    DeletionResponse,
    DocumentPatch,
    IngestionResponse,
    SearchRequest,
    SearchResponse,
    TextDocumentRequest,
)
from app.services.knowledge.rag import service
from app.services.knowledge.rag.security import admin_access, signing_key, verify_token
from app.services.knowledge.rag.settings import RagError
from app.services.knowledge.rag.storage import DocumentStorage

router = APIRouter(
    prefix="/api/v1/admin/knowledge-configs/{config_id}",
    tags=["knowledge-documents"],
    dependencies=[Depends(admin_access)],
)
citation_router = APIRouter(prefix="/api/v1/knowledge/citations", tags=["knowledge-citations"])


def public(model, fields: str) -> dict:
    """只序列化声明字段，禁止暴露对象键、租约令牌或内部异常。"""
    return {name: getattr(model, name) for name in fields.split()}


async def read_upload(file: UploadFile) -> bytes:
    """受限读取，避免无界读入上传内容。"""
    try:
        data = await file.read(settings.KNOWLEDGE_MAX_FILE_BYTES + 1)
        if len(data) > settings.KNOWLEDGE_MAX_FILE_BYTES:
            raise RagError("文件超过大小限制", 413)
        return data
    finally:
        await file.close()


@router.post("/rag/enable")
async def enable_rag(config_id: str):
    """显式启用独立索引，不自动迁移旧集合。"""
    signing_key()
    return await service.enable(config_id)


@router.post("/documents/upload", status_code=202, response_model=IngestionResponse)
async def upload_document(
    config_id: str,
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=300),
    independent: bool = Form(default=False),
):
    """保存原文件并排队，成功响应不代表已完成索引。"""
    return await service.enqueue(
        config_id,
        await read_upload(file),
        file.filename or "",
        file.content_type or "",
        title,
        independent=independent,
    )


@router.post("/documents/text", status_code=202, response_model=IngestionResponse)
async def create_text(config_id: str, body: TextDocumentRequest):
    """粘贴文本也保存原始 UTF-8 文件，以支持一致的下载与重建。"""
    return await service.enqueue(
        config_id,
        body.text.encode(),
        "article.md" if body.markdown else "article.txt",
        "text/plain",
        body.title,
        independent=body.independent,
        source_type="text",
    )


@router.get("/documents")
async def list_documents(
    config_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_deleted: bool = False,
):
    """分页查询文章和最新处理状态，当前版本与待处理版本分开显示。"""
    async with get_db_context() as db:
        await service.source(db, config_id)
        conditions = [Document.config_id == config_id]
        if not include_deleted:
            conditions.append(Document.deleted.is_(False))
        total = await db.scalar(select(func.count()).select_from(Document).where(*conditions))
        docs = (
            await db.scalars(
                select(Document)
                .where(*conditions)
                .order_by(Document.created_at.desc(), Document.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        items = []
        for doc in docs:
            item = public(
                doc,
                "id config_id title source_type current_revision_id enabled deleted cleaned created_at updated_at",
            )
            latest = await db.scalar(
                select(DocumentRevision)
                .where(DocumentRevision.document_id == doc.id)
                .order_by(DocumentRevision.version.desc())
                .limit(1)
            )
            item["latest_revision"] = public(latest, "id version status error") if latest else None
            items.append(item)
        return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/documents/{document_id}")
async def get_document(config_id: str, document_id: str):
    """列出所有历史版本元信息，全文通过单独接口按需读取。"""
    async with get_db_context() as db:
        doc = await service.document(db, config_id, document_id, allow_deleted=True)
        revisions = (
            await db.scalars(
                select(DocumentRevision)
                .where(DocumentRevision.document_id == doc.id)
                .order_by(DocumentRevision.version.desc())
            )
        ).all()
        result = public(
            doc,
            "id config_id title source_type current_revision_id enabled deleted cleaned created_at updated_at",
        )
        result["revisions"] = [
            public(
                r,
                "id version filename mime_type size file_hash parser_version chunk_size chunk_overlap status error created_at",
            )
            for r in revisions
        ]
        return result


@router.patch("/documents/{document_id}")
async def patch_document(config_id: str, document_id: str, body: DocumentPatch):
    """修改展示标题或即时关闭后续召回，不改写版本正文。"""
    async with get_db_context() as db:
        doc = await service.document(db, config_id, document_id)
        for key, value in body.model_dump(exclude_unset=True).items():
            setattr(doc, key, value)
        await db.flush()
        return public(doc, "id title enabled current_revision_id")


@router.post(
    "/documents/{document_id}/revisions", status_code=202, response_model=IngestionResponse
)
async def replace_document(
    config_id: str,
    document_id: str,
    file: UploadFile | None = File(default=None),
    text: str | None = Form(default=None),
    markdown: bool = Form(default=False),
):
    """multipart 中 file 与 text 二选一，建立新版本并保持当前版本服务。"""
    if (file is None) == (text is None):
        raise RagError("必须且只能提供 file 或 text")
    if file:
        data, filename, mime = await read_upload(file), file.filename or "", file.content_type or ""
    else:
        data, filename, mime = (
            text.encode(),
            "article.md" if markdown else "article.txt",
            "text/plain",
        )
    return await service.enqueue(config_id, data, filename, mime, None, document_id=document_id)


@router.post("/documents/{document_id}/reindex", status_code=202, response_model=IngestionResponse)
async def reindex_document(config_id: str, document_id: str):
    """以当前全局处理配置重新建立版本。"""
    return await service.reindex(config_id, document_id)


@router.delete("/documents/{document_id}", status_code=202, response_model=DeletionResponse)
async def delete_document(config_id: str, document_id: str):
    """立即撤销检索资格，后台可恢复地清理所有原文和向量。"""
    return await service.delete_document(config_id, document_id)


@router.get("/documents/{document_id}/content", response_model=ContentResponse)
async def document_content(config_id: str, document_id: str, revision_id: str | None = None):
    """读取规范化全文，偏移按 Unicode 字符而非字节或 token 计算。"""
    async with get_db_context() as db:
        doc = await service.document(db, config_id, document_id)
        rev = await service.revision(db, doc, revision_id)
        if rev.full_text is None:
            raise RagError("全文尚未解析完成", 409)
        return {"document_id": doc.id, "revision_id": rev.id, "text": rev.full_text}


@router.get("/documents/{document_id}/chunks")
async def document_chunks(
    config_id: str,
    document_id: str,
    revision_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """分页读取精确段落边界，避免把整篇文章作为检索调试结果发送。"""
    async with get_db_context() as db:
        doc = await service.document(db, config_id, document_id)
        rev = await service.revision(db, doc, revision_id)
        condition = DocumentChunk.revision_id == rev.id
        total = await db.scalar(select(func.count()).select_from(DocumentChunk).where(condition))
        chunks = (
            await db.scalars(
                select(DocumentChunk)
                .where(condition)
                .order_by(DocumentChunk.chunk_index)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return {
            "items": [
                public(
                    c,
                    "id revision_id chunk_index content start_offset end_offset page heading_path",
                )
                for c in chunks
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
        }


def original_response(data: bytes, filename: str, mime: str) -> Response:
    """附件下载阻止浏览器把上传内容当作可执行页面展示。"""
    return Response(
        data,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/documents/{document_id}/original")
async def document_original(config_id: str, document_id: str, revision_id: str | None = None):
    """仅管理者可直接按文章和版本下载原始文件。"""
    async with get_db_context() as db:
        doc = await service.document(db, config_id, document_id)
        rev = await service.revision(db, doc, revision_id)
    return original_response(
        await DocumentStorage().get(rev.object_key), rev.filename, rev.mime_type
    )


@router.get("/jobs/{job_id}")
async def get_job(config_id: str, job_id: str):
    """跨知识源的任务 ID 不可读取，租约 token 不返回。"""
    async with get_db_context() as db:
        job = await db.get(IngestionJob, job_id)
        if not job:
            raise RagError("任务不存在", 404)
        await service.document(db, config_id, job.document_id, allow_deleted=True)
        return public(
            job,
            "id document_id revision_id kind status progress attempts available_at error created_at updated_at",
        )


@router.post("/jobs/{job_id}/retry", status_code=202, response_model=IngestionResponse)
async def retry_job(config_id: str, job_id: str):
    """只重试已失败任务，不抢占正在执行或已成功发布的任务。"""
    async with get_db_context() as db:
        await db.execute(
            update(KnowledgeConfig)
            .where(KnowledgeConfig.id == config_id)
            .values(name=KnowledgeConfig.name)
        )
        await service.source(db, config_id)
        job = await db.get(IngestionJob, job_id)
        if not job:
            raise RagError("任务不存在", 404)
        doc = await service.document(db, config_id, job.document_id)
        pending = await db.scalar(
            select(IngestionJob.id).where(
                IngestionJob.document_id == doc.id,
                IngestionJob.id != job.id,
                IngestionJob.status.in_(service.ACTIVE_JOBS),
            )
        )
        if pending:
            raise RagError("该文章已有执行中的任务", 409)
        if job.status != "failed":
            raise RagError("仅失败任务可手动重试", 409)
        rev = await db.get(DocumentRevision, job.revision_id)
        latest = await db.scalar(
            select(func.max(DocumentRevision.version)).where(DocumentRevision.document_id == doc.id)
        )
        if not rev or rev.version != latest:
            raise RagError("旧失败版本不能覆盖较新的版本", 409)
        from app.services.knowledge.rag.settings import embedding_profile

        if rev.profile["embedding"] != embedding_profile():
            raise RagError("模型配置已改变，请重新索引", 409)
        result = await db.execute(
            update(IngestionJob)
            .where(IngestionJob.id == job.id, IngestionJob.status == "failed")
            .values(
                status="queued",
                attempts=0,
                error=None,
                progress=0,
                token=None,
                lease_until=0,
                available_at=0,
            )
        )
        if result.rowcount != 1:
            raise RagError("任务已被其他请求更新", 409)
        rev.status, rev.error = "queued", None
        return {"document_id": doc.id, "revision_id": rev.id, "job_id": job.id, "status": "queued"}


@router.post("/search", response_model=SearchResponse)
async def search_documents(config_id: str, body: SearchRequest):
    """与 Agent 使用同一检索服务，返回可核对的 SQL 分块。"""
    return {"items": await service.search(config_id, body.query)}


@citation_router.get("/{citation_id}")
async def read_citation(
    citation_id: str, token: str = Query(..., max_length=2048), original: bool = False
):
    """签名仅授权这一消息引用的文章版本，不提供自由浏览知识库的能力。"""
    claims = verify_token(token)
    async with get_db_context() as db:
        row = await db.get(MessageCitation, citation_id)
        if (
            not row
            or claims.get("i") != row.id
            or claims.get("m") != row.message_id
            or claims.get("c") != row.conversation_id
            or claims.get("r") != row.revision_id
        ):
            raise RagError("引用不存在或凭证不匹配", 403)
        doc = await db.get(Document, row.document_id)
        if not doc or doc.deleted:
            raise RagError("原文已删除", 410)
        rev = await service.revision(db, doc, row.revision_id)
        chunk = await db.get(DocumentChunk, row.chunk_id)
        if not chunk or chunk.revision_id != rev.id:
            raise RagError("原文段落已不可用", 410)
        result = {
            **row.snapshot,
            "text": rev.full_text,
            "original_url": f"/api/v1/knowledge/citations/{row.id}?token={quote(token)}&original=true",
        }
    if original:
        return original_response(
            await DocumentStorage().get(rev.object_key), rev.filename, rev.mime_type
        )
    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse

    return JSONResponse(
        jsonable_encoder(result),
        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"},
    )
