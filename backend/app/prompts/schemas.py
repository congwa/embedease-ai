"""提示词 Pydantic Schemas"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PromptCategory(str, Enum):
    """提示词分类"""

    AGENT = "agent"
    MEMORY = "memory"
    SKILL = "skill"
    CRAWLER = "crawler"


class PromptSource(str, Enum):
    """提示词来源"""

    DEFAULT = "default"  # 代码默认值
    CUSTOM = "custom"  # 用户自定义


class PromptBase(BaseModel):
    """提示词基础字段"""

    name: str = Field(..., description="显示名称")
    description: str | None = Field(None, description="提示词说明")
    content: str = Field(..., description="提示词内容")
    variables: list[str] = Field(default_factory=list, description="支持的模板变量")


class PromptCreate(PromptBase):
    """创建提示词"""

    key: str = Field(..., description="提示词唯一标识")
    category: PromptCategory = Field(..., description="分类")


class PromptUpdate(BaseModel):
    """更新提示词"""

    name: str | None = Field(None, description="显示名称")
    description: str | None = Field(None, description="提示词说明")
    content: str | None = Field(None, description="提示词内容")
    is_active: bool | None = Field(None, description="是否启用")


class PromptResponse(PromptBase):
    """提示词响应"""

    key: str = Field(..., description="提示词唯一标识")
    category: PromptCategory = Field(..., description="分类")
    source: PromptSource = Field(..., description="来源：default 或 custom")
    is_active: bool = Field(True, description="是否启用")
    default_content: str | None = Field(None, description="默认内容（仅 custom 时返回）")
    created_at: datetime | None = Field(None, description="创建时间")
    updated_at: datetime | None = Field(None, description="更新时间")

    model_config = {"from_attributes": True}


class PromptListResponse(BaseModel):
    """提示词列表响应"""

    items: list[PromptResponse]
    total: int


class PromptResetResponse(BaseModel):
    """重置提示词响应"""

    key: str
    message: str
    content: str = Field(..., description="重置后的内容（默认值）")
