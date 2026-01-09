"""聊天相关 Schema"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.config import settings

ChatMode = Literal["natural", "free", "strict"]


class ImageAttachment(BaseModel):
    """图片附件"""

    id: str = Field(..., description="图片唯一 ID")
    url: str = Field(..., description="图片 URL")
    thumbnail_url: str | None = Field(None, description="缩略图 URL")
    filename: str | None = Field(None, description="原始文件名")
    size: int | None = Field(None, description="文件大小（字节）")
    width: int | None = Field(None, description="图片宽度")
    height: int | None = Field(None, description="图片高度")
    mime_type: str | None = Field(None, description="MIME 类型")


class ChatRequest(BaseModel):
    """聊天请求"""

    user_id: str = Field(..., description="用户 ID")
    conversation_id: str = Field(..., description="会话 ID")
    message: str = Field("", description="用户消息（可为空，但必须有图片）")
    images: list[ImageAttachment] | None = Field(
        default=None,
        description="图片附件列表",
    )
    mode: ChatMode | None = Field(
        default=None,
        description="聊天模式：natural（商品推荐）、free（自由聊天）、strict（严格模式）",
    )
    agent_id: str | None = Field(
        default=None,
        description="智能体 ID，为空时使用默认智能体",
    )

    @property
    def effective_mode(self) -> ChatMode:
        """获取有效的聊天模式（优先使用请求中的 mode，否则使用配置默认值）"""
        if self.mode is not None:
            return self.mode
        cfg_mode = settings.CHAT_MODE
        if cfg_mode in ("natural", "free", "strict"):
            return cfg_mode  # type: ignore[return-value]
        return "natural"

    @property
    def has_images(self) -> bool:
        """是否包含图片"""
        return bool(self.images and len(self.images) > 0)


class ChatEvent(BaseModel):
    """聊天事件（SSE）"""

    # legacy:
    # 该 Schema 是旧版协议（text/products/done/error）。新版统一协议请使用：
    # - `app.schemas.stream.StreamEvent`（对外 SSE）
    # - `app.schemas.events.StreamEventType`（事件类型枚举）
    type: Literal["text", "products", "done", "error"] = Field(..., description="事件类型")
    content: str | None = Field(None, description="文本内容")
    data: Any | None = Field(None, description="数据（商品列表等）")
    message_id: str | None = Field(None, description="消息 ID")
