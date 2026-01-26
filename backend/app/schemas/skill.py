"""技能 Schema 定义"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SkillType(str, Enum):
    """技能类型"""

    SYSTEM = "system"
    USER = "user"
    AI_GENERATED = "ai"


class SkillCategory(str, Enum):
    """技能分类"""

    PROMPT = "prompt"
    RETRIEVAL = "retrieval"
    TOOL = "tool"
    WORKFLOW = "workflow"


class SkillBase(BaseModel):
    """技能基础字段"""

    name: str = Field(..., min_length=1, max_length=100, description="技能名称")
    description: str = Field(..., min_length=10, description="技能描述")
    category: SkillCategory = Field(default=SkillCategory.PROMPT, description="技能分类")
    content: str = Field(..., min_length=10, description="技能内容（Markdown）")
    trigger_keywords: list[str] = Field(default_factory=list, description="触发关键词")
    trigger_intents: list[str] = Field(default_factory=list, description="触发意图")
    always_apply: bool = Field(default=False, description="是否始终应用")
    applicable_agents: list[str] = Field(
        default_factory=list,
        description="适用的 Agent 类型",
    )
    applicable_modes: list[str] = Field(
        default_factory=list,
        description="适用的模式",
    )


class SkillCreate(SkillBase):
    """创建技能请求"""

    pass


class SkillUpdate(BaseModel):
    """更新技能请求"""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=10)
    category: SkillCategory | None = None
    content: str | None = Field(None, min_length=10)
    trigger_keywords: list[str] | None = None
    trigger_intents: list[str] | None = None
    always_apply: bool | None = None
    applicable_agents: list[str] | None = None
    applicable_modes: list[str] | None = None
    is_active: bool | None = None


class SkillRead(SkillBase):
    """技能读取响应"""

    id: str
    type: SkillType
    version: str
    author: str | None
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillListResponse(BaseModel):
    """技能列表响应"""

    items: list[SkillRead]
    total: int
    page: int
    page_size: int


# ========== AI 生成相关 ==========


class SkillGenerateRequest(BaseModel):
    """AI 生成技能请求"""

    description: str = Field(..., min_length=20, description="技能描述")
    category: SkillCategory | None = Field(None, description="分类建议")
    applicable_agents: list[str] = Field(default_factory=list, description="适用 Agent")
    examples: list[str] | None = Field(None, description="示例对话")


class SkillGenerateResponse(BaseModel):
    """AI 生成技能响应"""

    skill: SkillCreate
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class SkillRefineRequest(BaseModel):
    """技能优化请求"""

    feedback: str = Field(..., min_length=10, description="优化反馈")


# ========== Agent 技能配置 ==========


class AgentSkillConfig(BaseModel):
    """Agent 技能配置项"""

    skill_id: str
    priority: int = Field(default=100, ge=1, le=1000)
    is_enabled: bool = True


class AgentSkillsUpdate(BaseModel):
    """更新 Agent 技能配置"""

    skills: list[AgentSkillConfig]


class AgentSkillRead(BaseModel):
    """Agent 技能读取"""

    skill_id: str
    skill_name: str
    skill_description: str
    priority: int
    is_enabled: bool

    model_config = {"from_attributes": True}
