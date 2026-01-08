"""Quick Setup 快捷配置中心 Schema

定义 Quick Setup 向导的状态、检查清单、步骤配置等数据模型。
"""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ========== 枚举类型 ==========


class SetupStepStatus(StrEnum):
    """步骤状态"""

    PENDING = "pending"  # 待完成
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    SKIPPED = "skipped"  # 已跳过


class ChecklistItemStatus(StrEnum):
    """检查项状态"""

    OK = "ok"  # 已配置
    DEFAULT = "default"  # 使用默认值
    MISSING = "missing"  # 未配置
    ERROR = "error"  # 配置错误


# ========== Checklist ==========


class ChecklistItem(BaseModel):
    """单个检查项"""

    key: str = Field(..., description="配置项标识")
    label: str = Field(..., description="显示名称")
    category: str = Field(..., description="所属类别")
    status: ChecklistItemStatus = Field(..., description="状态")
    current_value: str | None = Field(default=None, description="当前值（脱敏）")
    default_value: str | None = Field(default=None, description="默认值")
    description: str | None = Field(default=None, description="说明")
    step_index: int | None = Field(default=None, description="关联的步骤索引")


class ChecklistResponse(BaseModel):
    """检查清单响应"""

    items: list[ChecklistItem] = Field(default_factory=list)
    total: int = Field(default=0)
    ok_count: int = Field(default=0)
    default_count: int = Field(default=0)
    missing_count: int = Field(default=0)


# ========== Setup State ==========


class SetupStep(BaseModel):
    """单个步骤"""

    index: int = Field(..., description="步骤索引")
    key: str = Field(..., description="步骤标识")
    title: str = Field(..., description="步骤标题")
    description: str | None = Field(default=None, description="步骤描述")
    status: SetupStepStatus = Field(default=SetupStepStatus.PENDING)
    data: dict[str, Any] | None = Field(default=None, description="步骤数据")


class QuickSetupState(BaseModel):
    """Quick Setup 状态"""

    completed: bool = Field(default=False, description="是否已完成")
    current_step: int = Field(default=0, description="当前步骤索引")
    steps: list[SetupStep] = Field(default_factory=list, description="所有步骤")
    agent_id: str | None = Field(default=None, description="当前配置的 Agent ID")
    updated_at: datetime | None = Field(default=None, description="最后更新时间")


class QuickSetupStateUpdate(BaseModel):
    """更新 Quick Setup 状态"""

    completed: bool | None = Field(default=None)
    current_step: int | None = Field(default=None)
    steps: list[SetupStep] | None = Field(default=None)
    agent_id: str | None = Field(default=None)


# ========== Agent Type Config ==========


class AgentTypeField(BaseModel):
    """Agent 类型配置字段"""

    key: str = Field(..., description="字段标识")
    label: str = Field(..., description="显示名称")
    type: Literal["text", "textarea", "select", "multiselect", "switch", "number"] = Field(...)
    required: bool = Field(default=False)
    default: Any = Field(default=None)
    options: list[dict[str, str]] | None = Field(default=None, description="选项列表")
    description: str | None = Field(default=None)
    group: str | None = Field(default=None, description="所属分组")


class AgentTypeStepConfig(BaseModel):
    """Agent 类型特定步骤配置"""

    step_key: str = Field(..., description="步骤标识")
    enabled: bool = Field(default=True, description="是否启用此步骤")
    title_override: str | None = Field(default=None, description="标题覆盖")
    description_override: str | None = Field(default=None, description="描述覆盖")
    fields: list[AgentTypeField] = Field(default_factory=list, description="额外字段")
    hints: list[str] = Field(default_factory=list, description="提示信息")


class AgentTypeConfig(BaseModel):
    """Agent 类型完整配置"""

    type: Literal["product", "faq", "kb", "custom"] = Field(..., description="Agent 类型")
    name: str = Field(..., description="类型名称")
    description: str = Field(..., description="类型描述")
    icon: str = Field(default="Bot", description="图标名称")
    default_tool_categories: list[str] = Field(default_factory=list)
    default_middleware_flags: dict[str, bool] = Field(default_factory=dict)
    default_knowledge_type: str | None = Field(default=None)
    steps: list[AgentTypeStepConfig] = Field(default_factory=list, description="类型特定步骤配置")
    greeting_template: dict[str, Any] | None = Field(default=None, description="开场白模板")
    system_prompt_template: str | None = Field(default=None, description="系统提示词模板")


class AgentTypeConfigListResponse(BaseModel):
    """Agent 类型配置列表响应"""

    items: list[AgentTypeConfig] = Field(default_factory=list)


# ========== Step Data ==========


class SystemSettingsStepData(BaseModel):
    """系统基础设置步骤数据"""

    company_name: str | None = Field(default=None, max_length=100)
    brand_theme: str | None = Field(default=None, max_length=50)
    language: str = Field(default="zh-CN")
    timezone: str = Field(default="Asia/Shanghai")
    admin_contact: str | None = Field(default=None, max_length=200)


class ModelSettingsStepData(BaseModel):
    """模型配置步骤数据（只读展示，实际配置需修改 .env）"""

    llm_provider: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    qdrant_host: str | None = None
    qdrant_port: int | None = None
    qdrant_collection: str | None = None


class KnowledgeStepData(BaseModel):
    """知识配置步骤数据"""

    knowledge_config_id: str | None = Field(default=None)
    tool_categories: list[str] | None = Field(default=None)
    middleware_flags: dict[str, bool] | None = Field(default=None)
    # FAQ 特定
    faq_count: int | None = Field(default=None)
    faq_unindexed: int | None = Field(default=None)
    # KB 特定
    top_k: int | None = Field(default=None)
    similarity_threshold: float | None = Field(default=None)
    rerank_enabled: bool | None = Field(default=None)


class GreetingStepData(BaseModel):
    """开场白配置步骤数据"""

    enabled: bool = Field(default=False)
    trigger: Literal["first_visit", "every_session"] = Field(default="first_visit")
    delay_ms: int = Field(default=1000)
    channels: dict[str, dict[str, Any]] = Field(default_factory=dict)
    cta: dict[str, str] | None = Field(default=None)


class ChannelStepData(BaseModel):
    """渠道配置步骤数据"""

    web_enabled: bool = Field(default=True)
    support_enabled: bool = Field(default=False)
    webhook_url: str | None = Field(default=None)
    # 暂不支持的渠道
    slack_enabled: bool = Field(default=False, description="暂不支持")
    wework_enabled: bool = Field(default=False, description="通过 .env 配置")


# ========== Health Check ==========


class ServiceHealthItem(BaseModel):
    """服务健康检查项"""

    name: str
    status: Literal["ok", "error", "unknown"]
    message: str | None = None
    latency_ms: float | None = None


class HealthCheckResponse(BaseModel):
    """健康检查响应"""

    services: list[ServiceHealthItem] = Field(default_factory=list)
    all_ok: bool = Field(default=False)
