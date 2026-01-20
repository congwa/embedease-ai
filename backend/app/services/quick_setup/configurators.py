"""Agent 类型配置器（多态架构）

每种 Agent 类型（Product/FAQ/KB/Custom）有独立的配置器实现，
通过注册表模式管理，方便扩展新类型。
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.schemas.quick_setup import (
    AgentTypeConfig,
    AgentTypeField,
    AgentTypeStepConfig,
)


class AgentTypeConfigurator(ABC):
    """Agent 类型配置器基类
    
    定义了所有 Agent 类型配置器必须实现的接口。
    每个子类负责定义特定类型的：
    - 默认配置（工具、中间件、知识源等）
    - 步骤配置（哪些步骤启用、额外字段等）
    - 模板（系统提示词、开场白等）
    - 验证逻辑
    """

    # 类型标识，子类必须覆盖
    agent_type: ClassVar[str] = ""

    @property
    @abstractmethod
    def name(self) -> str:
        """类型显示名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """类型描述"""
        pass

    @property
    def icon(self) -> str:
        """图标名称（Lucide icon）"""
        return "Bot"

    @property
    @abstractmethod
    def default_tool_categories(self) -> list[str]:
        """默认工具类别"""
        pass

    @property
    def default_middleware_flags(self) -> dict[str, Any]:
        """默认中间件配置（开关 + 参数）"""
        return {
            "todo_enabled": True,
            "summarization_enabled": True,
            "tool_retry_enabled": True,
            "tool_limit_enabled": True,
            "memory_enabled": True,
            # 默认不启用滑动窗口和噪音过滤，由子类覆盖
            "sliding_window_enabled": None,
            "noise_filter_enabled": None,
        }

    @property
    def default_knowledge_type(self) -> str | None:
        """默认知识源类型"""
        return None

    @property
    def system_prompt_template(self) -> str | None:
        """系统提示词模板"""
        return None

    @property
    def greeting_template(self) -> dict[str, Any] | None:
        """开场白模板"""
        return None

    @abstractmethod
    def get_step_configs(self) -> list[AgentTypeStepConfig]:
        """获取类型特定的步骤配置"""
        pass

    def get_knowledge_step_fields(self) -> list[AgentTypeField]:
        """获取知识配置步骤的额外字段（可覆盖）"""
        return []

    def get_greeting_step_hints(self) -> list[str]:
        """获取开场白步骤的提示信息（可覆盖）"""
        return []

    def validate_step_data(self, step_key: str, data: dict[str, Any]) -> list[str]:
        """验证步骤数据，返回错误列表（可覆盖）"""
        return []

    def get_config(self) -> AgentTypeConfig:
        """获取完整的类型配置"""
        return AgentTypeConfig(
            type=self.agent_type,  # type: ignore
            name=self.name,
            description=self.description,
            icon=self.icon,
            default_tool_categories=self.default_tool_categories,
            default_middleware_flags=self.default_middleware_flags,
            default_knowledge_type=self.default_knowledge_type,
            steps=self.get_step_configs(),
            greeting_template=self.greeting_template,
            system_prompt_template=self.system_prompt_template,
        )


class ProductAgentConfigurator(AgentTypeConfigurator):
    """商品推荐 Agent 配置器"""

    agent_type: ClassVar[str] = "product"

    @property
    def name(self) -> str:
        return "商品推荐助手"

    @property
    def description(self) -> str:
        return "专注商品搜索、推荐、比较，帮助用户发现和购买商品"

    @property
    def icon(self) -> str:
        return "ShoppingCart"

    @property
    def default_tool_categories(self) -> list[str]:
        return ["search", "query", "compare", "filter", "category", "featured", "purchase", "guide"]

    @property
    def default_middleware_flags(self) -> dict[str, Any]:
        """商品推荐 Agent 默认启用噪音过滤（压缩商品描述）"""
        return {
            "todo_enabled": True,
            "summarization_enabled": True,
            "tool_retry_enabled": True,
            "tool_limit_enabled": True,
            "memory_enabled": True,
            # 商品场景：启用噪音过滤，压缩商品描述
            "noise_filter_enabled": True,
            "noise_filter_max_chars": 2000,
            # 滑动窗口使用全局默认
            "sliding_window_enabled": None,
        }

    @property
    def default_knowledge_type(self) -> str | None:
        return "product"

    @property
    def system_prompt_template(self) -> str | None:
        return """你是一个专业的商品推荐助手。

你的目标是：
1. 理解用户的购物需求和偏好
2. 使用工具搜索和筛选商品
3. 提供个性化的商品推荐
4. 帮助用户比较和选择商品

回答要求：
- 推荐时简明扼要，突出商品亮点
- 主动询问用户的具体需求（预算、用途、偏好等）
- 非商品相关问题，引导回商品话题"""

    @property
    def greeting_template(self) -> dict[str, Any] | None:
        return {
            "enabled": True,
            "trigger": "first_visit",
            "delay_ms": 1000,
            "channels": {
                "default": {
                    "title": "👋 欢迎光临",
                    "body": "您好！我是您的专属购物助手，可以帮您搜索商品、比较价格、推荐适合您的产品。\n\n有什么可以帮您的吗？",
                },
                "web": {
                    "title": "👋 欢迎光临",
                    "body": "您好！我是您的专属购物助手。\n\n**我可以帮您：**\n- 🔍 搜索和筛选商品\n- 📊 比较不同商品\n- 💡 推荐热门好物",
                },
            },
            "cta": {"text": "开始购物", "payload": "推荐一些热门商品"},
        }

    def get_step_configs(self) -> list[AgentTypeStepConfig]:
        return [
            AgentTypeStepConfig(
                step_key="knowledge",
                enabled=True,
                title_override="商品数据配置",
                description_override="绑定商品数据源，配置搜索和推荐工具",
                fields=self.get_knowledge_step_fields(),
                hints=[
                    "确保商品数据已导入到 Qdrant 向量库",
                    "工具类别决定了 Agent 可用的商品操作能力",
                    "启用 memory_enabled 可让 Agent 记住用户偏好",
                ],
            ),
            AgentTypeStepConfig(
                step_key="greeting",
                enabled=True,
                hints=["销售型开场白应突出促销信息和热门商品"],
            ),
            AgentTypeStepConfig(
                step_key="channel",
                enabled=True,
                hints=["可配置商城落地页 URL，方便用户直接下单"],
            ),
        ]

    def get_knowledge_step_fields(self) -> list[AgentTypeField]:
        return [
            AgentTypeField(
                key="tool_categories",
                label="工具类别",
                type="multiselect",
                required=True,
                default=self.default_tool_categories,
                options=[
                    {"value": "search", "label": "搜索商品"},
                    {"value": "query", "label": "查询详情"},
                    {"value": "compare", "label": "对比商品"},
                    {"value": "filter", "label": "筛选过滤"},
                    {"value": "category", "label": "分类浏览"},
                    {"value": "featured", "label": "热门推荐"},
                    {"value": "purchase", "label": "购买引导"},
                    {"value": "guide", "label": "选购指南"},
                ],
                description="选择 Agent 可使用的工具类别",
                group="tools",
            ),
            AgentTypeField(
                key="catalog_profile_enabled",
                label="启用商品画像",
                type="switch",
                default=True,
                description="自动分析商品库生成画像，优化搜索效果",
                group="advanced",
            ),
        ]


class FAQAgentConfigurator(AgentTypeConfigurator):
    """FAQ 问答 Agent 配置器"""

    agent_type: ClassVar[str] = "faq"

    @property
    def name(self) -> str:
        return "FAQ 问答助手"

    @property
    def description(self) -> str:
        return "基于 FAQ 知识库回答常见问题，适合客服场景"

    @property
    def icon(self) -> str:
        return "MessageCircleQuestion"

    @property
    def default_tool_categories(self) -> list[str]:
        return ["faq_search"]

    @property
    def default_middleware_flags(self) -> dict[str, Any]:
        """FAQ Agent 默认配置：启用滑动窗口（对话通常较短）"""
        return {
            "todo_enabled": False,
            "summarization_enabled": True,
            "tool_retry_enabled": True,
            "tool_limit_enabled": True,
            "memory_enabled": False,
            # FAQ 场景：启用滑动窗口，对话通常较短
            "sliding_window_enabled": True,
            "sliding_window_strategy": "messages",
            "sliding_window_max_messages": 30,
            # 噪音过滤：FAQ 输出通常简洁，不需要过滤
            "noise_filter_enabled": False,
        }

    @property
    def default_knowledge_type(self) -> str | None:
        return "faq"

    @property
    def system_prompt_template(self) -> str | None:
        return """你是一个专业的客服问答助手。

你的目标是：
1. 准确理解用户的问题
2. 从 FAQ 知识库中检索最相关的答案
3. 用简洁清晰的语言回答用户

回答要求：
- 基于 FAQ 内容回答，不要编造信息
- 如果找不到答案，诚实告知并建议人工客服
- 回答简洁明了，避免冗长"""

    @property
    def greeting_template(self) -> dict[str, Any] | None:
        return {
            "enabled": True,
            "trigger": "first_visit",
            "delay_ms": 800,
            "channels": {
                "default": {
                    "title": "👋 您好",
                    "body": "欢迎使用智能客服！我可以帮您解答常见问题。",
                },
                "support": {
                    "title": "🎧 客服支持",
                    "body": "您好，我是智能客服助手。\n\n请描述您的问题，我会尽力为您解答。如需人工服务，可随时告诉我。",
                },
            },
            "cta": {"text": "常见问题", "payload": "有哪些常见问题？"},
        }

    def get_step_configs(self) -> list[AgentTypeStepConfig]:
        return [
            AgentTypeStepConfig(
                step_key="knowledge",
                enabled=True,
                title_override="FAQ 知识库配置",
                description_override="管理 FAQ 条目，确保知识库完整",
                fields=self.get_knowledge_step_fields(),
                hints=[
                    "至少创建 1 条 FAQ 条目才能使用",
                    "未索引的 FAQ 无法被检索，请确保索引状态",
                    "定期维护 FAQ，保持答案的时效性",
                ],
            ),
            AgentTypeStepConfig(
                step_key="greeting",
                enabled=True,
                hints=["客服型开场白应体现专业和亲和力"],
            ),
            AgentTypeStepConfig(
                step_key="channel",
                enabled=True,
                hints=["建议配置 support 渠道的专属入口"],
            ),
        ]

    def get_knowledge_step_fields(self) -> list[AgentTypeField]:
        return [
            AgentTypeField(
                key="faq_stats",
                label="FAQ 统计",
                type="text",
                description="当前 FAQ 条目数量和状态",
                group="stats",
            ),
            AgentTypeField(
                key="top_k",
                label="检索数量",
                type="number",
                default=5,
                description="每次检索返回的 FAQ 条目数",
                group="retrieval",
            ),
            AgentTypeField(
                key="similarity_threshold",
                label="相似度阈值",
                type="number",
                default=0.5,
                description="低于此阈值的结果将被过滤",
                group="retrieval",
            ),
        ]

    def validate_step_data(self, step_key: str, data: dict[str, Any]) -> list[str]:
        errors = []
        if step_key == "knowledge":
            faq_count = data.get("faq_count", 0)
            if faq_count == 0:
                errors.append("FAQ 知识库为空，请至少创建 1 条 FAQ 条目")
        return errors


class KBAgentConfigurator(AgentTypeConfigurator):
    """知识库 Agent 配置器"""

    agent_type: ClassVar[str] = "kb"

    @property
    def name(self) -> str:
        return "知识库助手"

    @property
    def description(self) -> str:
        return "基于文档向量检索回答问题，适合内部知识库场景"

    @property
    def icon(self) -> str:
        return "BookOpen"

    @property
    def default_tool_categories(self) -> list[str]:
        return ["kb_search", "kb_query"]

    @property
    def default_middleware_flags(self) -> dict[str, Any]:
        """KB Agent 默认配置：启用摘要和噪音过滤（文档检索结果可能很长）"""
        return {
            "todo_enabled": False,
            "summarization_enabled": True,
            "summarization_trigger_messages": 40,
            "summarization_keep_messages": 15,
            "tool_retry_enabled": True,
            "tool_limit_enabled": True,
            "memory_enabled": True,
            # KB 场景：启用噪音过滤，压缩文档内容
            "noise_filter_enabled": True,
            "noise_filter_max_chars": 3000,
            # 滑动窗口使用全局默认
            "sliding_window_enabled": None,
        }

    @property
    def default_knowledge_type(self) -> str | None:
        return "vector"

    @property
    def system_prompt_template(self) -> str | None:
        return """你是一个知识库检索助手。

你的目标是：
1. 理解用户的查询意图
2. 从知识库中检索相关文档
3. 基于检索结果准确回答问题

回答要求：
- 必须基于知识库内容回答
- 引用来源时标注文档名称
- 如果知识库中没有相关内容，明确告知用户"""

    @property
    def greeting_template(self) -> dict[str, Any] | None:
        return {
            "enabled": True,
            "trigger": "first_visit",
            "delay_ms": 800,
            "channels": {
                "default": {
                    "title": "📚 知识库助手",
                    "body": "您好！我可以帮您检索和查询知识库内容。请描述您想了解的信息。",
                },
            },
        }

    def get_step_configs(self) -> list[AgentTypeStepConfig]:
        return [
            AgentTypeStepConfig(
                step_key="knowledge",
                enabled=True,
                title_override="知识库配置",
                description_override="配置向量检索参数和文档来源",
                fields=self.get_knowledge_step_fields(),
                hints=[
                    "上传文档后需要重建索引才能检索",
                    "启用 Rerank 可提升检索准确性",
                    "建议设置 similarity_threshold 过滤低质量结果",
                ],
            ),
            AgentTypeStepConfig(
                step_key="greeting",
                enabled=True,
                hints=["强调自助知识库的信息检索能力"],
            ),
        ]

    def get_knowledge_step_fields(self) -> list[AgentTypeField]:
        return [
            AgentTypeField(
                key="collection_name",
                label="向量集合",
                type="text",
                required=True,
                description="Qdrant 向量集合名称",
                group="vector",
            ),
            AgentTypeField(
                key="top_k",
                label="检索数量",
                type="number",
                default=10,
                description="每次检索返回的文档数",
                group="retrieval",
            ),
            AgentTypeField(
                key="similarity_threshold",
                label="相似度阈值",
                type="number",
                default=0.6,
                description="低于此阈值的结果将被过滤",
                group="retrieval",
            ),
            AgentTypeField(
                key="rerank_enabled",
                label="启用重排序",
                type="switch",
                default=False,
                description="使用 Rerank 模型优化检索结果排序",
                group="retrieval",
            ),
        ]


class CustomAgentConfigurator(AgentTypeConfigurator):
    """自定义 Agent 配置器"""

    agent_type: ClassVar[str] = "custom"

    @property
    def name(self) -> str:
        return "自定义助手"

    @property
    def description(self) -> str:
        return "完全自定义的 Agent，可自由配置工具、中间件和知识源"

    @property
    def icon(self) -> str:
        return "Wrench"

    @property
    def default_tool_categories(self) -> list[str]:
        return []

    @property
    def default_middleware_flags(self) -> dict[str, bool]:
        return {
            "todo_enabled": True,
            "summarization_enabled": True,
            "tool_retry_enabled": True,
            "tool_limit_enabled": True,
            "memory_enabled": True,
        }

    @property
    def system_prompt_template(self) -> str | None:
        return "你是一个智能助手。请根据用户的问题提供帮助。"

    def get_step_configs(self) -> list[AgentTypeStepConfig]:
        return [
            AgentTypeStepConfig(
                step_key="knowledge",
                enabled=True,
                title_override="自定义配置",
                description_override="自由配置工具类别、中间件和知识源",
                fields=self.get_knowledge_step_fields(),
                hints=[
                    "自定义类型可绑定任意知识源（FAQ/KB/Product）",
                    "通过 AgentModeOverride 可为不同场景定义专属模式",
                    "middleware_flags 完全自定义，按需启用",
                ],
            ),
            AgentTypeStepConfig(
                step_key="greeting",
                enabled=True,
            ),
            AgentTypeStepConfig(
                step_key="channel",
                enabled=True,
            ),
        ]

    def get_knowledge_step_fields(self) -> list[AgentTypeField]:
        return [
            AgentTypeField(
                key="knowledge_config_id",
                label="知识源",
                type="select",
                description="绑定已有的知识源配置",
                group="knowledge",
            ),
            AgentTypeField(
                key="tool_categories",
                label="工具类别",
                type="multiselect",
                options=[
                    {"value": "search", "label": "搜索"},
                    {"value": "query", "label": "查询"},
                    {"value": "compare", "label": "比较"},
                    {"value": "filter", "label": "筛选"},
                    {"value": "faq_search", "label": "FAQ 搜索"},
                    {"value": "kb_search", "label": "知识库搜索"},
                ],
                description="选择可用的工具类别",
                group="tools",
            ),
            AgentTypeField(
                key="middleware_flags",
                label="中间件配置",
                type="multiselect",
                options=[
                    {"value": "todo_enabled", "label": "TODO 规划"},
                    {"value": "summarization_enabled", "label": "上下文压缩"},
                    {"value": "tool_retry_enabled", "label": "工具重试"},
                    {"value": "tool_limit_enabled", "label": "工具限制"},
                    {"value": "memory_enabled", "label": "记忆系统"},
                ],
                description="选择启用的中间件",
                group="middleware",
            ),
        ]


# ========== 配置器注册表 ==========


_CONFIGURATOR_REGISTRY: dict[str, type[AgentTypeConfigurator]] = {
    "product": ProductAgentConfigurator,
    "faq": FAQAgentConfigurator,
    "kb": KBAgentConfigurator,
    "custom": CustomAgentConfigurator,
}


def get_configurator(agent_type: str) -> AgentTypeConfigurator:
    """获取指定类型的配置器实例"""
    configurator_cls = _CONFIGURATOR_REGISTRY.get(agent_type)
    if not configurator_cls:
        raise ValueError(f"未知的 Agent 类型: {agent_type}")
    return configurator_cls()


def get_all_configurators() -> list[AgentTypeConfigurator]:
    """获取所有配置器实例"""
    return [cls() for cls in _CONFIGURATOR_REGISTRY.values()]


def register_configurator(agent_type: str, configurator_cls: type[AgentTypeConfigurator]) -> None:
    """注册新的配置器（用于扩展）"""
    _CONFIGURATOR_REGISTRY[agent_type] = configurator_cls
