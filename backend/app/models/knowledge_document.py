"""托管知识库的原文、版本、任务与历史引用；SQL 是发布状态的唯一事实来源。"""

from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RagSource(Base, TimestampMixin):
    """显式启用的托管知识源，与旧向量知识源隔离。"""

    __tablename__ = "rag_sources"
    config_id: Mapped[str] = mapped_column(ForeignKey("knowledge_configs.id"), primary_key=True)


class Document(Base, TimestampMixin):
    """文章身份与当前已发布版本；删除标记先于外部资源清理。"""

    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    config_id: Mapped[str] = mapped_column(ForeignKey("knowledge_configs.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    source_type: Mapped[str] = mapped_column(String(20))
    current_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    cleaned: Mapped[bool] = mapped_column(Boolean, default=False)


class DocumentRevision(Base, TimestampMixin):
    """不可变处理配置与可回溯全文，重建产生新版本而非覆盖旧段落。"""

    __tablename__ = "knowledge_revisions"
    __table_args__ = (UniqueConstraint("document_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str] = mapped_column(String(300))
    filename: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    processing_hash: Mapped[str] = mapped_column(String(64), index=True)
    profile: Mapped[dict[str, Any]] = mapped_column(JSON)
    collection: Mapped[str] = mapped_column(String(100))
    parser_version: Mapped[str] = mapped_column(String(30), default="rag-v1")
    chunk_size: Mapped[int] = mapped_column(Integer)
    chunk_overlap: Mapped[int] = mapped_column(Integer)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class DocumentChunk(Base):
    """精确对应规范化全文切片的分块，ID 同时作为 Qdrant point ID。"""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("revision_id", "chunk_index"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey("knowledge_revisions.id"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list)


class IngestionJob(Base, TimestampMixin):
    """带数据库租约的可恢复任务；token 防止旧执行者发布结果。"""

    __tablename__ = "knowledge_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"), index=True)
    revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), default="ingest")
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[float] = mapped_column(Float, default=0, index=True)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    token: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class MessageCitation(Base, TimestampMixin):
    """历史引用快照，不级联引用原文实体，以便删除文章后仍可展示摘要。"""

    __tablename__ = "knowledge_message_citations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    message_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str] = mapped_column(String(36), index=True)
    revision_id: Mapped[str] = mapped_column(String(36))
    chunk_id: Mapped[str] = mapped_column(String(36))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
