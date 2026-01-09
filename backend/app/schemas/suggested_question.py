"""推荐问题 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class SuggestedQuestionBase(BaseModel):
    """推荐问题基础字段"""

    question: str = Field(..., min_length=1, max_length=200, description="问题文本")
    source: str = Field(default="manual", description="来源: manual/auto/faq")
    display_position: str = Field(default="both", description="展示位置: welcome/input/both")
    weight: int = Field(default=0, description="排序权重，越大越靠前")
    enabled: bool = Field(default=True, description="是否启用")
    start_time: datetime | None = Field(default=None, description="生效开始时间")
    end_time: datetime | None = Field(default=None, description="生效结束时间")


class SuggestedQuestionCreate(SuggestedQuestionBase):
    """创建推荐问题"""

    faq_entry_id: str | None = Field(default=None, description="关联的 FAQ ID")


class SuggestedQuestionUpdate(BaseModel):
    """更新推荐问题"""

    question: str | None = Field(default=None, min_length=1, max_length=200)
    display_position: str | None = Field(default=None)
    weight: int | None = Field(default=None)
    enabled: bool | None = Field(default=None)
    start_time: datetime | None = Field(default=None)
    end_time: datetime | None = Field(default=None)


class SuggestedQuestionResponse(SuggestedQuestionBase):
    """推荐问题响应"""

    id: str
    agent_id: str
    faq_entry_id: str | None
    click_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SuggestedQuestionPublicItem(BaseModel):
    """公开接口的单个问题"""

    id: str
    question: str


class SuggestedQuestionsPublicResponse(BaseModel):
    """公开接口响应 - 按位置分组"""

    welcome: list[SuggestedQuestionPublicItem] = Field(
        default_factory=list, description="欢迎区展示的问题"
    )
    input: list[SuggestedQuestionPublicItem] = Field(
        default_factory=list, description="输入框上方展示的问题"
    )


class SuggestedQuestionBatchCreate(BaseModel):
    """批量创建请求"""

    questions: list[str] = Field(..., min_length=1, description="问题列表")
    display_position: str = Field(default="both")


class SuggestedQuestionImportFromFAQ(BaseModel):
    """从 FAQ 导入请求"""

    category: str | None = Field(default=None, description="FAQ 分类过滤")
    limit: int = Field(default=5, ge=1, le=20, description="导入数量")
    display_position: str = Field(default="both")


class SuggestedQuestionReorder(BaseModel):
    """重新排序请求"""

    question_ids: list[str] = Field(..., min_length=1, description="按新顺序排列的问题 ID")
