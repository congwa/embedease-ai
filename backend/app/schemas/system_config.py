"""系统配置 Schema"""

from pydantic import BaseModel, Field


class LLMConfigBase(BaseModel):
    """LLM 配置基础字段"""

    provider: str = Field(default="siliconflow", description="LLM 提供商")
    api_key: str = Field(default="", description="API Key")
    base_url: str = Field(default="https://api.siliconflow.cn/v1", description="API Base URL")
    chat_model: str = Field(default="moonshotai/Kimi-K2-Thinking", description="聊天模型")


class EmbeddingConfigBase(BaseModel):
    """Embedding 配置基础字段"""

    provider: str = Field(default="siliconflow", description="Embedding 提供商")
    api_key: str | None = Field(default=None, description="API Key（留空使用 LLM 的）")
    base_url: str | None = Field(default=None, description="Base URL（留空使用 LLM 的）")
    model: str = Field(default="Qwen/Qwen3-Embedding-8B", description="Embedding 模型")
    dimension: int = Field(default=4096, description="Embedding 维度")


class RerankConfigBase(BaseModel):
    """Rerank 配置基础字段"""

    enabled: bool = Field(default=False, description="是否启用 Rerank")
    provider: str | None = Field(default=None, description="Rerank 提供商")
    api_key: str | None = Field(default=None, description="API Key")
    base_url: str | None = Field(default=None, description="Base URL")
    model: str | None = Field(default=None, description="Rerank 模型")
    top_n: int = Field(default=5, description="返回前 N 个结果")


class SystemConfigRead(BaseModel):
    """系统配置读取响应"""

    # 配置是否已初始化（数据库中是否有配置）
    initialized: bool = Field(default=False, description="配置是否已初始化")

    # LLM 配置
    llm: LLMConfigBase = Field(default_factory=LLMConfigBase)

    # Embedding 配置
    embedding: EmbeddingConfigBase = Field(default_factory=EmbeddingConfigBase)

    # Rerank 配置
    rerank: RerankConfigBase = Field(default_factory=RerankConfigBase)

    # 配置来源
    source: str = Field(default="env", description="配置来源: env | database")


class SystemConfigReadMasked(BaseModel):
    """系统配置读取响应（API Key 脱敏）"""

    initialized: bool = Field(default=False)

    # LLM 配置
    llm_provider: str
    llm_api_key_masked: str
    llm_base_url: str
    llm_chat_model: str

    # Embedding 配置
    embedding_provider: str
    embedding_api_key_masked: str | None
    embedding_base_url: str | None
    embedding_model: str
    embedding_dimension: int

    # Rerank 配置
    rerank_enabled: bool
    rerank_provider: str | None
    rerank_api_key_masked: str | None
    rerank_base_url: str | None
    rerank_model: str | None
    rerank_top_n: int

    # 配置来源
    source: str


class QuickConfigUpdate(BaseModel):
    """快速配置更新（只需 API Key）"""

    api_key: str = Field(..., min_length=1, description="API Key")
    provider: str = Field(default="siliconflow", description="LLM 提供商")
    base_url: str | None = Field(default=None, description="Base URL（可选，留空使用默认）")


class FullConfigUpdate(BaseModel):
    """完整配置更新"""

    # LLM 配置
    llm_provider: str = Field(..., description="LLM 提供商")
    llm_api_key: str = Field(..., min_length=1, description="API Key")
    llm_base_url: str = Field(..., description="Base URL")
    llm_chat_model: str = Field(..., description="聊天模型")

    # Embedding 配置
    embedding_provider: str = Field(..., description="Embedding 提供商")
    embedding_api_key: str | None = Field(default=None, description="Embedding API Key")
    embedding_base_url: str | None = Field(default=None, description="Embedding Base URL")
    embedding_model: str = Field(..., description="Embedding 模型")
    embedding_dimension: int = Field(..., ge=1, description="Embedding 维度")

    # Rerank 配置（可选）
    rerank_enabled: bool = Field(default=False, description="是否启用 Rerank")
    rerank_provider: str | None = Field(default=None, description="Rerank 提供商")
    rerank_api_key: str | None = Field(default=None, description="Rerank API Key")
    rerank_base_url: str | None = Field(default=None, description="Rerank Base URL")
    rerank_model: str | None = Field(default=None, description="Rerank 模型")
    rerank_top_n: int = Field(default=5, ge=1, description="Rerank Top N")


class ConfigTestRequest(BaseModel):
    """配置测试请求"""

    provider: str = Field(..., description="LLM 提供商")
    api_key: str = Field(..., min_length=1, description="API Key")
    base_url: str = Field(..., description="Base URL")
    model: str | None = Field(default=None, description="模型（可选，用于测试）")


class ConfigTestResponse(BaseModel):
    """配置测试响应"""

    success: bool
    message: str
    latency_ms: float | None = None
    models: list[str] | None = None  # 可用的模型列表


# 预置的提供商配置
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "siliconflow": {
        "name": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "moonshotai/Kimi-K2-Thinking",
        "default_embedding_model": "Qwen/Qwen3-Embedding-8B",
        "default_embedding_dimension": "4096",
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "default_embedding_model": "text-embedding-3-large",
        "default_embedding_dimension": "3072",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "default_embedding_model": "deepseek-embedding",
        "default_embedding_dimension": "1536",
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
        "default_embedding_model": "",
        "default_embedding_dimension": "0",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-3.5-sonnet",
        "default_embedding_model": "",
        "default_embedding_dimension": "0",
    },
}


class ProviderPreset(BaseModel):
    """提供商预设"""

    id: str
    name: str
    base_url: str
    default_model: str
    default_embedding_model: str
    default_embedding_dimension: int


class ProviderPresetsResponse(BaseModel):
    """提供商预设列表响应"""

    items: list[ProviderPreset]


# ========== Supervisor 全局配置 ==========


class SupervisorSubAgent(BaseModel):
    """Supervisor 子 Agent 配置"""

    agent_id: str = Field(..., description="Agent ID")
    name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    description: str | None = Field(default=None, max_length=500, description="描述")
    routing_hints: list[str] = Field(default_factory=list, description="路由关键词")
    priority: int = Field(default=100, ge=0, le=1000, description="优先级，越大越优先")


class SupervisorRoutingRule(BaseModel):
    """Supervisor 路由规则"""

    condition_type: str = Field(default="keyword", description="条件类型: keyword | intent")
    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    intents: list[str] = Field(default_factory=list, description="意图列表")
    target_agent_id: str = Field(..., description="目标 Agent ID")
    priority: int = Field(default=0, ge=0, le=1000, description="规则优先级")


class SupervisorRoutingPolicy(BaseModel):
    """Supervisor 路由策略"""

    type: str = Field(default="hybrid", description="策略类型: keyword | intent | hybrid")
    rules: list[SupervisorRoutingRule] = Field(default_factory=list, description="路由规则")
    default_agent_id: str | None = Field(default=None, description="默认 Agent ID")


class SupervisorGlobalConfig(BaseModel):
    """全局 Supervisor 配置"""

    enabled: bool = Field(default=False, description="是否启用 Supervisor 功能")
    supervisor_prompt: str | None = Field(default=None, description="调度器提示词")
    sub_agents: list[SupervisorSubAgent] = Field(default_factory=list, description="子 Agent 列表")
    routing_policy: SupervisorRoutingPolicy = Field(default_factory=SupervisorRoutingPolicy, description="路由策略")
    intent_timeout: float = Field(default=3.0, ge=0.5, le=30.0, description="意图分类超时（秒）")
    allow_multi_agent: bool = Field(default=False, description="是否允许多 Agent 协作")


class SupervisorGlobalConfigUpdate(BaseModel):
    """全局 Supervisor 配置更新"""

    enabled: bool | None = Field(default=None, description="是否启用 Supervisor 功能")
    supervisor_prompt: str | None = Field(default=None, description="调度器提示词")
    sub_agents: list[SupervisorSubAgent] | None = Field(default=None, description="子 Agent 列表")
    routing_policy: SupervisorRoutingPolicy | None = Field(default=None, description="路由策略")
    intent_timeout: float | None = Field(default=None, ge=0.5, le=30.0, description="意图分类超时（秒）")
    allow_multi_agent: bool | None = Field(default=None, description="是否允许多 Agent 协作")


class SupervisorGlobalConfigResponse(BaseModel):
    """全局 Supervisor 配置响应"""

    enabled: bool
    supervisor_prompt: str | None
    sub_agents: list[SupervisorSubAgent]
    routing_policy: SupervisorRoutingPolicy
    intent_timeout: float
    allow_multi_agent: bool
    source: str = Field(description="配置来源: env | database")


class AvailableAgentForSupervisor(BaseModel):
    """可选为子 Agent 的 Agent"""

    id: str
    name: str
    description: str | None
    type: str
    status: str
    is_selected: bool = Field(default=False, description="是否已加入子 Agent")
