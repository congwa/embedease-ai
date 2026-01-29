"""Agent 运行态配置 Schema

定义 Effective Config API 的响应模型，用于展示 Agent 最终生效的配置。
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ========== System Prompt 层级 ==========


class PromptLayer(BaseModel):
    """提示词层级"""

    name: str = Field(..., description="层级名称: base/mode_suffix/skill_injection")
    source: str = Field(..., description="来源说明")
    char_count: int = Field(..., description="字符数")
    content: str = Field(..., description="该层级的内容")
    skill_ids: list[str] | None = Field(default=None, description="技能 ID（仅 skill_injection）")


class EffectiveSystemPrompt(BaseModel):
    """最终生效的系统提示词"""

    final_content: str = Field(..., description="最终完整提示词")
    char_count: int = Field(..., description="总字符数")
    layers: list[PromptLayer] = Field(default_factory=list, description="各层级详情")


# ========== Skills ==========


class SkillInfo(BaseModel):
    """技能信息"""

    id: str
    name: str
    description: str | None = None
    priority: int = 100
    trigger_keywords: list[str] = Field(default_factory=list)
    content_preview: str | None = Field(default=None, description="内容预览（前200字符）")


class EffectiveSkills(BaseModel):
    """最终生效的技能"""

    always_apply: list[SkillInfo] = Field(default_factory=list, description="始终生效的技能")
    conditional: list[SkillInfo] = Field(default_factory=list, description="条件触发的技能")
    triggered_by_test_message: list[str] = Field(
        default_factory=list, description="测试消息触发的技能 ID"
    )


# ========== Tools ==========


class ToolInfo(BaseModel):
    """工具信息"""

    name: str
    description: str | None = None
    categories: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list, description="来源说明")


class FilteredToolInfo(BaseModel):
    """被过滤的工具"""

    name: str
    reason: str = Field(..., description="过滤原因")


class EffectiveTools(BaseModel):
    """最终生效的工具"""

    enabled: list[ToolInfo] = Field(default_factory=list)
    filtered: list[FilteredToolInfo] = Field(default_factory=list)


# ========== Middlewares ==========


class MiddlewareInfo(BaseModel):
    """中间件信息"""

    name: str
    order: int
    enabled: bool
    source: str = Field(..., description="配置来源")
    reason: str | None = Field(default=None, description="禁用原因（仅 enabled=false 时）")
    params: dict[str, Any] = Field(default_factory=dict, description="中间件参数")


class EffectiveMiddlewares(BaseModel):
    """最终生效的中间件"""

    pipeline: list[MiddlewareInfo] = Field(default_factory=list, description="启用的中间件（按执行顺序）")
    disabled: list[MiddlewareInfo] = Field(default_factory=list, description="未启用的中间件")


# ========== Knowledge ==========


class EffectiveKnowledge(BaseModel):
    """最终生效的知识源配置"""

    configured: bool = False
    type: str | None = None
    name: str | None = None
    index_name: str | None = None
    collection_name: str | None = None
    embedding_model: str | None = None
    top_k: int | None = None
    similarity_threshold: float | None = None
    rerank_enabled: bool = False
    data_version: str | None = None


# ========== Policies ==========


class PolicyValue(BaseModel):
    """策略值（含来源）"""

    value: Any
    source: str = Field(..., description="来源: agent/settings/mode")


class EffectiveToolPolicy(BaseModel):
    """工具调用策略"""

    min_tool_calls: PolicyValue
    allow_direct_answer: PolicyValue
    fallback_tool: PolicyValue | None = None
    clarification_tool: PolicyValue | None = None


class EffectivePolicies(BaseModel):
    """最终生效的策略配置"""

    mode: str
    tool_policy: EffectiveToolPolicy | None = None
    middleware_flags: dict[str, PolicyValue] = Field(default_factory=dict)


# ========== Health Check ==========


class EffectiveHealth(BaseModel):
    """配置健康度"""

    score: int = Field(..., ge=0, le=100, description="健康度分数")
    warnings: list[str] = Field(default_factory=list, description="警告项")
    passed: list[str] = Field(default_factory=list, description="通过项")


# ========== 完整响应 ==========


class EffectiveConfigResponse(BaseModel):
    """Agent 运行态配置完整响应"""

    # 基本信息
    agent_id: str
    name: str
    type: str
    mode: str
    config_version: str
    generated_at: datetime

    # 各模块配置
    system_prompt: EffectiveSystemPrompt
    skills: EffectiveSkills
    tools: EffectiveTools
    middlewares: EffectiveMiddlewares
    knowledge: EffectiveKnowledge
    policies: EffectivePolicies
    health: EffectiveHealth


# ========== 请求参数 ==========


class EffectiveConfigParams(BaseModel):
    """获取运行态配置的参数"""

    mode: str | None = Field(default=None, description="指定回答模式，默认使用 agent.mode_default")
    include_filtered: bool = Field(default=True, description="是否包含被过滤的工具/中间件")
    include_diff: bool = Field(default=False, description="是否包含配置来源 Diff")
    test_message: str | None = Field(default=None, description="模拟消息，用于预测技能触发")
