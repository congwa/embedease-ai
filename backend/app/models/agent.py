"""智能体配置模型

多 Agent 架构核心表：
- Agent: 智能体配置（类型、系统提示、工具/中间件开关等）
- KnowledgeConfig: 知识源配置（FAQ/向量/图谱等）
- AgentTool: Agent 工具白名单（可选精细化）
- FAQEntry: FAQ 条目存储
- SuggestedQuestion: 推荐问题
"""

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class AgentType(StrEnum):
    """智能体类型"""

    PRODUCT = "product"  # 商品推荐
    FAQ = "faq"  # FAQ 问答
    KB = "kb"  # 内部知识库
    CUSTOM = "custom"  # 自定义


class KnowledgeType(StrEnum):
    """知识源类型"""

    FAQ = "faq"  # FAQ 问答库
    VECTOR = "vector"  # 向量检索
    GRAPH = "graph"  # 知识图谱
    PRODUCT = "product"  # 商品库（复用现有）
    HTTP_API = "http_api"  # 外部 API
    MIXED = "mixed"  # 混合


class AgentStatus(StrEnum):
    """智能体状态"""

    ENABLED = "enabled"
    DISABLED = "disabled"


class KnowledgeConfig(Base, TimestampMixin):
    """知识源配置表

    描述各类知识源的检索配置，如 FAQ 索引、向量库、知识图谱等。
    """

    __tablename__ = "knowledge_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(
        String(20),
        default=KnowledgeType.VECTOR.value,
        nullable=False,
    )

    # 索引/集合配置
    index_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    collection_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 嵌入模型配置
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 检索参数
    top_k: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    similarity_threshold: Mapped[float | None] = mapped_column(nullable=True)
    rerank_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 额外过滤条件（JSON）
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 数据版本（用于缓存失效）
    data_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 关联
    agents: Mapped[list["Agent"]] = relationship("Agent", back_populates="knowledge_config")


class Agent(Base, TimestampMixin):
    """智能体配置表

    核心配置表，定义每个智能体的类型、提示词、工具集、中间件等。
    运行时按 (agent_id, mode) 缓存 Agent 实例。
    """

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 类型
    type: Mapped[str] = mapped_column(
        String(20),
        default=AgentType.PRODUCT.value,
        nullable=False,
        index=True,
    )

    # 系统提示词
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # 默认回答策略模式
    mode_default: Mapped[str] = mapped_column(
        String(20),
        default="natural",
        nullable=False,
    )

    # 中间件开关（JSON，覆盖默认配置）
    # 格式: {"todo_enabled": true, "summarization_enabled": false, ...}
    middleware_flags: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 工具策略覆盖（JSON）
    # 格式: {"min_tool_calls": 1, "allow_direct_answer": false, "fallback_tool": "guide_user"}
    tool_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 允许的工具类别（JSON 数组）
    # 格式: ["search", "query", "compare", "faq", "kb"]
    tool_categories: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # 知识源绑定
    knowledge_config_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("knowledge_configs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 结构化输出格式（可选，按 type 默认）
    response_format: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(
        String(20),
        default=AgentStatus.ENABLED.value,
        nullable=False,
        index=True,
    )

    # 是否为默认 Agent
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 开场白配置（JSON）
    # 格式: {"enabled": true, "trigger": "first_visit", "delay_ms": 1500, "channels": {...}, "cta": {...}}
    greeting_config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 关联
    knowledge_config: Mapped["KnowledgeConfig | None"] = relationship(
        "KnowledgeConfig",
        back_populates="agents",
    )
    tools: Mapped[list["AgentTool"]] = relationship(
        "AgentTool",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    faq_entries: Mapped[list["FAQEntry"]] = relationship(
        "FAQEntry",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    suggested_questions: Mapped[list["SuggestedQuestion"]] = relationship(
        "SuggestedQuestion",
        back_populates="agent",
        cascade="all, delete-orphan",
    )


class AgentTool(Base):
    """Agent 工具白名单表（可选精细化控制）

    如果需要精确到工具级别的开关，使用此表；
    否则通过 Agent.tool_categories 按类别控制即可。
    """

    __tablename__ = "agent_tools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 关联
    agent: Mapped["Agent"] = relationship("Agent", back_populates="tools")


class FAQEntry(Base, TimestampMixin):
    """FAQ 条目表

    存储 FAQ 问答对，支持按 Agent 隔离或共享。
    """

    __tablename__ = "faq_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 可选绑定到特定 Agent（为空则全局共享）
    agent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 问题与答案
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # 分类与标签
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # 来源
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # 优先级/排序
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 是否启用
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 向量 ID（如果已索引到向量库）
    vector_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 关联
    agent: Mapped["Agent | None"] = relationship("Agent", back_populates="faq_entries")


class SuggestedQuestion(Base, TimestampMixin):
    """推荐问题表

    存储每个 Agent 的推荐问题，支持手动配置和热门统计。
    展示在聊天界面的欢迎区和输入框上方。
    """

    __tablename__ = "suggested_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 绑定到 Agent
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 问题文本
    question: Mapped[str] = mapped_column(String(200), nullable=False)

    # 来源类型：manual(手动) / auto(自动统计) / faq(从FAQ导入)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)

    # 关联的 FAQ ID（可选）
    faq_entry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("faq_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 排序权重（越大越靠前）
    weight: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 热度统计
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 展示位置：welcome(欢迎区) / input(输入框上方) / both(两处都展示)
    display_position: Mapped[str] = mapped_column(String(20), default="both", nullable=False)

    # 是否启用
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 生效时间范围（可选）
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关联
    agent: Mapped["Agent"] = relationship("Agent", back_populates="suggested_questions")


class AgentModeOverride(Base):
    """Agent 模式覆盖表（可选）

    允许为同一 Agent 的不同 mode 配置不同的提示词/策略。
    """

    __tablename__ = "agent_mode_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)

    # 覆盖配置
    system_prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_policy_override: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    middleware_overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
