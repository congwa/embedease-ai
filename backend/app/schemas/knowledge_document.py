"""托管知识文档管理请求；响应由路由提供稳定的业务字段。"""

from pydantic import BaseModel, Field, model_validator


class TextDocumentRequest(BaseModel):
    """UTF-8 文本或 Markdown 文章，默认相同原文件和处理配置复用。"""

    title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=2_000_000)
    markdown: bool = False
    independent: bool = False


class DocumentPatch(BaseModel):
    """标题和启停可立即变更，正文更新必须创建新版本。"""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    enabled: bool | None = None

    @model_validator(mode="after")
    def no_explicit_null(self):
        """禁止把非空数据库字段改成 null。"""
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("标题和启停状态不能为 null")
        return self


class SearchRequest(BaseModel):
    """检索范围来自路径，不能由查询正文覆盖知识源。"""

    query: str = Field(min_length=1, max_length=4000)


class IngestionResponse(BaseModel):
    """统一入库收据，202 表示排队或复用已有处理结果。"""

    document_id: str
    revision_id: str
    job_id: str
    status: str


class DeletionResponse(BaseModel):
    """删除任务收据，实际清理结果通过 job 查询。"""

    document_id: str
    job_id: str
    status: str


class ChunkResponse(BaseModel):
    """全文字符偏移和结构定位，不使用客户端生成的坐标。"""

    id: str
    revision_id: str
    chunk_index: int
    content: str
    start_offset: int
    end_offset: int
    page: int | None
    heading_path: list[str]


class SearchHit(BaseModel):
    """经过 SQL 二次验证的当前可见分块。"""

    id: str
    chunk_id: str
    document_id: str
    revision_id: str
    title: str
    content: str
    page: int | None
    heading_path: list[str]
    start_offset: int
    end_offset: int
    score: float


class SearchResponse(BaseModel):
    """检索调试与 Agent 共用排序结果。"""

    items: list[SearchHit]


class ContentResponse(BaseModel):
    """保存的规范化全文，而非分块拼接结果。"""

    document_id: str
    revision_id: str
    text: str
