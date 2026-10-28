"""聊天相关 Schema"""

from pydantic import BaseModel, Field


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
    agent_id: str | None = Field(
        default=None,
        description="智能体 ID；省略时沿用会话绑定，未绑定会话使用默认智能体",
    )

    @property
    def has_images(self) -> bool:
        """是否包含图片"""
        return bool(self.images and len(self.images) > 0)


