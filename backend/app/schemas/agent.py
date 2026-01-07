"""智能体相关 Schema

定义 Agent、KnowledgeConfig、FAQ 等的 API 请求/响应模型。
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ========== 枚举类型 ==========

AgentTypeEnum = Literal["product", "faq", "kb", "custom"]
KnowledgeTypeEnum = Literal["faq", "vector", "graph", "product", "http_api", "mixed"]
AgentStatusEnum = Literal["enabled", "disabled"]
ChatModeEnum = Literal["natural", "free", "strict"]
GreetingTriggerEnum = Literal["first_visit", "every_session"]


# ========== 开场白配置 ==========


class GreetingCTASchema(BaseModel):
    """开场白 CTA 按钮"""

    text: str = Field(..., min_length=1, max_length=50, description="按钮文本")
    payload: str = Field(..., max_length=200, description="点击后触发的消息/动作")


class GreetingChannelSchema(BaseModel):
    """单个渠道的开场白配置"""

    title: str | None = Field(default=None, max_length=100, description="标题")
    subtitle: str | None = Field(default=None, max_length=200, description="副标题")
    body: str = Field(..., min_length=1, description="正文内容（Markdown）")
    cta: GreetingCTASchema | None = Field(default=None, description="渠道专属 CTA")


class GreetingConfigSchema(BaseModel):
    """开场白完整配置"""

    enabled: bool = Field(default=False, description="是否启用开场白")
    trigger: GreetingTriggerEnum = Field(
        default="first_visit", description="触发策略：首次访问/每次会话"
    )
    delay_ms: int = Field(default=1000, ge=0, le=10000, description="展示延迟（毫秒）")
    channels: dict[str, GreetingChannelSchema] = Field(
        default_factory=dict, description="渠道配置（web/support/api/default）"
    )
    cta: GreetingCTASchema | None = Field(default=None, description="默认 CTA")
    variables: list[str] | None = Field(
        default=None, description="自定义变量列表（如 product_name）"
    )


class GreetingConfigUpdate(BaseModel):
    """更新开场白配置"""

    enabled: bool | None = Field(default=None)
    trigger: GreetingTriggerEnum | None = Field(default=None)
    delay_ms: int | None = Field(default=None, ge=0, le=10000)
    channels: dict[str, GreetingChannelSchema] | None = Field(default=None)
    cta: GreetingCTASchema | None = Field(default=None)
    variables: list[str] | None = Field(default=None)


# ========== 工具策略 ==========


class ToolPolicySchema(BaseModel):
    """工具调用策略"""

    min_tool_calls: int = Field(default=0, description="最小工具调用次数")
    allow_direct_answer: bool = Field(default=True, description="是否允许直接回答")
    fallback_tool: str | None = Field(default=None, description="无工具调用时的回退工具")
    clarification_tool: str | None = Field(default=None, description="信息不足时的澄清工具")


class MiddlewareFlagsSchema(BaseModel):
    """中间件开关配置"""

    todo_enabled: bool | None = Field(default=None, description="TODO 规划中间件")
    summarization_enabled: bool | None = Field(default=None, description="上下文压缩")
    tool_retry_enabled: bool | None = Field(default=None, description="工具重试")
    tool_limit_enabled: bool | None = Field(default=None, description="工具调用限制")
    memory_enabled: bool | None = Field(default=None, description="记忆系统")
    strict_mode_enabled: bool | None = Field(default=None, description="严格模式检查")


# ========== Knowledge Config ==========


class KnowledgeConfigBase(BaseModel):
    """知识源配置基础"""

    name: str = Field(..., min_length=1, max_length=100)
    type: KnowledgeTypeEnum = Field(default="vector")
    index_name: str | None = Field(default=None, max_length=100)
    collection_name: str | None = Field(default=None, max_length=100)
    embedding_model: str | None = Field(default=None, max_length=100)
    top_k: int = Field(default=10, ge=1, le=100)
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)
    rerank_enabled: bool = Field(default=False)
    filters: dict[str, Any] | None = Field(default=None)


class KnowledgeConfigCreate(KnowledgeConfigBase):
    """创建知识源配置"""

    pass


class KnowledgeConfigUpdate(BaseModel):
    """更新知识源配置"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: KnowledgeTypeEnum | None = Field(default=None)
    index_name: str | None = Field(default=None)
    collection_name: str | None = Field(default=None)
    embedding_model: str | None = Field(default=None)
    top_k: int | None = Field(default=None, ge=1, le=100)
    similarity_threshold: float | None = Field(default=None, ge=0, le=1)
    rerank_enabled: bool | None = Field(default=None)
    filters: dict[str, Any] | None = Field(default=None)


class KnowledgeConfigResponse(KnowledgeConfigBase):
    """知识源配置响应"""

    id: str
    data_version: str | None = None
    fingerprint: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========== Agent ==========


class AgentBase(BaseModel):
    """智能体基础配置"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    type: AgentTypeEnum = Field(default="product")
    system_prompt: str = Field(..., min_length=1)
    mode_default: ChatModeEnum = Field(default="natural")
    middleware_flags: dict[str, Any] | None = Field(default=None)
    tool_policy: dict[str, Any] | None = Field(default=None)
    tool_categories: list[str] | None = Field(default=None)
    knowledge_config_id: str | None = Field(default=None)
    response_format: str | None = Field(default=None)
    status: AgentStatusEnum = Field(default="enabled")
    is_default: bool = Field(default=False)
    greeting_config: GreetingConfigSchema | None = Field(default=None, description="开场白配置")


class AgentCreate(AgentBase):
    """创建智能体"""

    pass


class AgentUpdate(BaseModel):
    """更新智能体"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None)
    type: AgentTypeEnum | None = Field(default=None)
    system_prompt: str | None = Field(default=None, min_length=1)
    mode_default: ChatModeEnum | None = Field(default=None)
    middleware_flags: dict[str, Any] | None = Field(default=None)
    tool_policy: dict[str, Any] | None = Field(default=None)
    tool_categories: list[str] | None = Field(default=None)
    knowledge_config_id: str | None = Field(default=None)
    response_format: str | None = Field(default=None)
    status: AgentStatusEnum | None = Field(default=None)
    is_default: bool | None = Field(default=None)
    greeting_config: GreetingConfigSchema | None = Field(default=None)


class AgentResponse(AgentBase):
    """智能体响应"""

    id: str
    created_at: datetime
    updated_at: datetime
    knowledge_config: KnowledgeConfigResponse | None = None

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """智能体列表响应"""

    items: list[AgentResponse]
    total: int


# ========== Agent Tool ==========


class AgentToolBase(BaseModel):
    """Agent 工具白名单"""

    tool_name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = Field(default=True)


class AgentToolCreate(AgentToolBase):
    """创建工具白名单"""

    pass


class AgentToolUpdate(BaseModel):
    """更新工具白名单"""

    enabled: bool


class AgentToolResponse(AgentToolBase):
    """工具白名单响应"""

    id: int
    agent_id: str

    model_config = {"from_attributes": True}


# ========== FAQ Entry ==========


class FAQEntryBase(BaseModel):
    """FAQ 条目基础"""

    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    category: str | None = Field(default=None, max_length=100)
    tags: list[str] | None = Field(default=None)
    source: str | None = Field(default=None, max_length=200)
    priority: int = Field(default=0)
    enabled: bool = Field(default=True)


class FAQEntryCreate(FAQEntryBase):
    """创建 FAQ 条目"""

    agent_id: str | None = Field(default=None)


class FAQEntryUpdate(BaseModel):
    """更新 FAQ 条目"""

    question: str | None = Field(default=None, min_length=1)
    answer: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    source: str | None = Field(default=None)
    priority: int | None = Field(default=None)
    enabled: bool | None = Field(default=None)


class FAQEntryResponse(FAQEntryBase):
    """FAQ 条目响应"""

    id: str
    agent_id: str | None
    vector_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FAQImportRequest(BaseModel):
    """FAQ 批量导入请求"""

    agent_id: str | None = Field(default=None, description="绑定的 Agent ID")
    entries: list[FAQEntryBase] = Field(..., min_length=1)
    rebuild_index: bool = Field(default=True, description="导入后是否重建索引")


class FAQImportResponse(BaseModel):
    """FAQ 导入响应"""

    imported_count: int
    skipped_count: int
    errors: list[str] = Field(default_factory=list)


# ========== 运行时配置（内部使用） ==========


class AgentConfig(BaseModel):
    """运行时 Agent 配置（从 DB 加载后的完整配置）

    用于 AgentService 构建 Agent 实例。
    """

    agent_id: str
    name: str
    type: AgentTypeEnum
    system_prompt: str
    mode: ChatModeEnum

    # 工具配置
    tool_categories: list[str] | None = None
    tool_whitelist: list[str] | None = None  # 从 agent_tools 加载
    tool_policy: ToolPolicySchema | None = None

    # 中间件配置
    middleware_flags: MiddlewareFlagsSchema | None = None

    # 知识源
    knowledge_config: KnowledgeConfigResponse | None = None

    # 输出格式
    response_format: str | None = None

    # 版本（用于缓存失效）
    config_version: str | None = None

    model_config = {"from_attributes": True}
