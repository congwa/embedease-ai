"""Agent 运行态配置构建器

构建 Agent 最终生效的配置，包含来源追踪和健康度检查。
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.logging import get_logger
from app.prompts.registry import get_default_prompt_content
from app.schemas.effective_config import (
    EffectiveConfigResponse,
    EffectiveHealth,
    EffectiveKnowledge,
    EffectiveMiddlewares,
    EffectivePolicies,
    EffectiveSkills,
    EffectiveSystemPrompt,
    EffectiveToolPolicy,
    EffectiveTools,
    FilteredToolInfo,
    MiddlewareInfo,
    PolicyValue,
    PromptLayer,
    SkillInfo,
    ToolInfo,
)
from app.services.agent.core.config import (
    DEFAULT_PROMPTS,
    DEFAULT_TOOL_CATEGORIES,
    DEFAULT_TOOL_POLICIES,
    AgentConfigLoader,
)
from app.services.agent.core.factory import MODE_PROMPT_SUFFIX
from app.services.agent.tools.registry import _get_tool_specs
from app.services.skill.registry import skill_registry

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.agent import Agent

logger = get_logger("agent.effective_config")


class EffectiveConfigBuilder:
    """运行态配置构建器"""

    def __init__(self, session: "AsyncSession"):
        self._session = session
        self._config_loader = AgentConfigLoader(session)

    async def build(
        self,
        agent: "Agent",
        mode: str | None = None,
        include_filtered: bool = True,
        test_message: str | None = None,
    ) -> EffectiveConfigResponse:
        """构建运行态配置

        Args:
            agent: Agent 实例
            mode: 指定模式，默认使用 agent.mode_default
            include_filtered: 是否包含被过滤的工具/中间件
            test_message: 测试消息，用于预测技能触发

        Returns:
            完整的运行态配置响应
        """
        effective_mode = mode or agent.mode_default

        # 获取 AgentConfig（用于工具和中间件构建）
        agent_config = await self._config_loader.load_config(agent.id, effective_mode)

        # 计算配置版本
        import hashlib
        config_version = hashlib.md5(f"{agent.id}:{agent.updated_at}".encode()).hexdigest()[:16]

        # 构建各模块配置
        system_prompt = self._build_system_prompt(agent, effective_mode)
        skills = self._build_skills(agent.type, effective_mode, test_message)
        tools = self._build_tools(agent_config, include_filtered) if agent_config else EffectiveTools(enabled=[], filtered=[])
        middlewares = self._build_middlewares(agent_config, include_filtered) if agent_config else EffectiveMiddlewares(pipeline=[], disabled=[])
        knowledge = self._build_knowledge(agent)
        policies = self._build_policies(agent, effective_mode)
        health = self._build_health(system_prompt, skills, tools, middlewares, knowledge)

        return EffectiveConfigResponse(
            agent_id=agent.id,
            name=agent.name,
            type=agent.type,
            mode=effective_mode,
            config_version=agent_config.config_version if agent_config else config_version,
            generated_at=datetime.now(timezone.utc),
            system_prompt=system_prompt,
            skills=skills,
            tools=tools,
            middlewares=middlewares,
            knowledge=knowledge,
            policies=policies,
            health=health,
        )

    def _build_system_prompt(self, agent: "Agent", mode: str) -> EffectiveSystemPrompt:
        """构建系统提示词信息"""
        layers: list[PromptLayer] = []

        # Layer 1: 基础提示词
        if agent.system_prompt:
            base_content = agent.system_prompt
            base_source = "agent.system_prompt (自定义)"
        else:
            base_content = DEFAULT_PROMPTS.get(agent.type, DEFAULT_PROMPTS["custom"])
            base_source = f"DEFAULT_PROMPTS[{agent.type}] (默认模板)"

        layers.append(
            PromptLayer(
                name="base",
                source=base_source,
                char_count=len(base_content),
                content=base_content,
            )
        )

        # Layer 2: 模式后缀
        mode_suffix = MODE_PROMPT_SUFFIX.get(mode, "")
        layers.append(
            PromptLayer(
                name="mode_suffix",
                source=f"agent.mode.{mode}",
                char_count=len(mode_suffix),
                content=mode_suffix,
            )
        )

        # Layer 3: 技能注入（always_apply）
        always_apply_skills = skill_registry.get_always_apply_skills(agent.type, mode)
        skill_context = skill_registry.build_skill_context(always_apply_skills)
        skill_ids = [s.id for s in always_apply_skills]

        layers.append(
            PromptLayer(
                name="skill_injection",
                source=f"always_apply_skills ({len(always_apply_skills)} 个)",
                char_count=len(skill_context),
                content=skill_context,
                skill_ids=skill_ids if skill_ids else None,
            )
        )

        # 最终内容
        final_content = base_content
        if mode_suffix:
            final_content = final_content + mode_suffix
        if skill_context:
            final_content = final_content + "\n\n" + skill_context

        return EffectiveSystemPrompt(
            final_content=final_content,
            char_count=len(final_content),
            layers=layers,
        )

    def _build_skills(
        self,
        agent_type: str,
        mode: str,
        test_message: str | None,
    ) -> EffectiveSkills:
        """构建技能信息"""
        always_apply: list[SkillInfo] = []
        conditional: list[SkillInfo] = []
        triggered_ids: list[str] = []

        # 获取所有可用技能
        all_skills = skill_registry.get_skills_for_agent(agent_type, mode)

        for skill in all_skills:
            info = SkillInfo(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                priority=skill.priority or 100,
                trigger_keywords=skill.trigger_keywords or [],
                content_preview=skill.content[:200] if skill.content else None,
            )

            if skill.always_apply:
                always_apply.append(info)
            else:
                conditional.append(info)

        # 测试消息触发
        if test_message:
            matched = skill_registry.match_skills(agent_type, mode, test_message)
            triggered_ids = [s.id for s in matched if not s.always_apply]

        return EffectiveSkills(
            always_apply=always_apply,
            conditional=conditional,
            triggered_by_test_message=triggered_ids,
        )

    def _build_tools(
        self,
        config: Any,
        include_filtered: bool,
    ) -> EffectiveTools:
        """构建工具信息"""
        enabled: list[ToolInfo] = []
        filtered: list[FilteredToolInfo] = []

        all_specs = _get_tool_specs()
        mode = config.mode

        for spec in all_specs:
            sources: list[str] = []
            filter_reason: str | None = None

            # 检查是否启用
            if not spec.enabled:
                filter_reason = "工具已禁用 (enabled=false)"
            elif spec.modes is not None and mode not in spec.modes:
                filter_reason = f"模式不匹配 (需要 {spec.modes}, 当前 {mode})"
            elif config.tool_categories:
                if any(c in spec.categories for c in config.tool_categories):
                    sources.append(f"类别匹配 ({', '.join(set(spec.categories) & set(config.tool_categories))})")
                else:
                    filter_reason = f"类别 {spec.categories} 不在 tool_categories 配置中"
            else:
                sources.append("默认启用")

            # 白名单检查
            if not filter_reason and config.tool_whitelist is not None:
                if spec.name in config.tool_whitelist:
                    sources.append("白名单")
                else:
                    filter_reason = "不在 tool_whitelist 白名单中"

            if filter_reason:
                if include_filtered:
                    filtered.append(FilteredToolInfo(name=spec.name, reason=filter_reason))
            else:
                enabled.append(
                    ToolInfo(
                        name=spec.name,
                        description=getattr(spec.tool, "__doc__", None),
                        categories=spec.categories,
                        sources=sources,
                    )
                )

        # 类型专用工具
        if config.type == "faq":
            enabled.append(
                ToolInfo(
                    name="faq_search",
                    description="FAQ 知识库检索",
                    categories=["knowledge"],
                    sources=["Agent 类型注入 (faq)"],
                )
            )
        elif config.type == "kb":
            enabled.append(
                ToolInfo(
                    name="kb_search",
                    description="知识库检索",
                    categories=["knowledge"],
                    sources=["Agent 类型注入 (kb)"],
                )
            )

        return EffectiveTools(enabled=enabled, filtered=filtered)

    def _build_middlewares(
        self,
        config: Any,
        include_filtered: bool,
    ) -> EffectiveMiddlewares:
        """构建中间件信息"""
        pipeline: list[MiddlewareInfo] = []
        disabled: list[MiddlewareInfo] = []

        flags = config.middleware_flags
        mode = config.mode

        # 中间件定义列表
        middleware_defs = [
            {
                "name": "MemoryOrchestration",
                "order": 10,
                "check": lambda: settings.MEMORY_ENABLED and settings.MEMORY_ORCHESTRATION_ENABLED,
                "flag_key": "memory_enabled",
                "settings_key": "MEMORY_ENABLED",
                "params": {},
            },
            {
                "name": "ResponseSanitization",
                "order": 20,
                "check": lambda: True,
                "flag_key": None,
                "settings_key": None,
                "params": {
                    "enabled": settings.RESPONSE_SANITIZATION_ENABLED,
                    "custom_message": settings.RESPONSE_SANITIZATION_CUSTOM_MESSAGE,
                },
            },
            {
                "name": "SSE",
                "order": 30,
                "check": lambda: True,
                "flag_key": None,
                "settings_key": None,
                "params": {},
            },
            {
                "name": "TodoList",
                "order": 40,
                "check": lambda: self._is_enabled(flags, "todo_enabled", "AGENT_TODO_ENABLED"),
                "flag_key": "todo_enabled",
                "settings_key": "AGENT_TODO_ENABLED",
                "params": {},
            },
            {
                "name": "SequentialToolExecution",
                "order": 50,
                "check": lambda: settings.AGENT_SERIALIZE_TOOLS,
                "flag_key": None,
                "settings_key": "AGENT_SERIALIZE_TOOLS",
                "params": {},
            },
            {
                "name": "NoiseFilter",
                "order": 55,
                "check": lambda: self._is_enabled(flags, "noise_filter_enabled", "AGENT_NOISE_FILTER_ENABLED"),
                "flag_key": "noise_filter_enabled",
                "settings_key": "AGENT_NOISE_FILTER_ENABLED",
                "params": {
                    "max_output_chars": self._get_value(flags, "noise_filter_max_chars", settings.AGENT_NOISE_FILTER_MAX_CHARS),
                    "preserve_head": self._get_value(flags, "noise_filter_preserve_head", settings.AGENT_NOISE_FILTER_PRESERVE_HEAD),
                    "preserve_tail": self._get_value(flags, "noise_filter_preserve_tail", settings.AGENT_NOISE_FILTER_PRESERVE_TAIL),
                },
            },
            {
                "name": "Logging",
                "order": 60,
                "check": lambda: True,
                "flag_key": None,
                "settings_key": None,
                "params": {},
            },
            {
                "name": "ToolRetry",
                "order": 70,
                "check": lambda: self._is_enabled(flags, "tool_retry_enabled", "AGENT_TOOL_RETRY_ENABLED"),
                "flag_key": "tool_retry_enabled",
                "settings_key": "AGENT_TOOL_RETRY_ENABLED",
                "params": {
                    "max_retries": settings.AGENT_TOOL_RETRY_MAX_RETRIES,
                    "backoff_factor": settings.AGENT_TOOL_RETRY_BACKOFF_FACTOR,
                },
            },
            {
                "name": "ToolCallLimit",
                "order": 80,
                "check": lambda: self._is_enabled(flags, "tool_limit_enabled", "AGENT_TOOL_LIMIT_ENABLED"),
                "flag_key": "tool_limit_enabled",
                "settings_key": "AGENT_TOOL_LIMIT_ENABLED",
                "params": {
                    "thread_limit": settings.AGENT_TOOL_LIMIT_THREAD,
                    "run_limit": settings.AGENT_TOOL_LIMIT_RUN,
                },
            },
            {
                "name": "SlidingWindow",
                "order": 85,
                "check": lambda: self._is_enabled(flags, "sliding_window_enabled", "AGENT_SLIDING_WINDOW_ENABLED"),
                "flag_key": "sliding_window_enabled",
                "settings_key": "AGENT_SLIDING_WINDOW_ENABLED",
                "params": {
                    "strategy": self._get_value(flags, "sliding_window_strategy", settings.AGENT_SLIDING_WINDOW_STRATEGY),
                    "max_messages": self._get_value(flags, "sliding_window_max_messages", settings.AGENT_SLIDING_WINDOW_MAX_MESSAGES),
                    "max_tokens": self._get_value(flags, "sliding_window_max_tokens", settings.AGENT_SLIDING_WINDOW_MAX_TOKENS),
                },
            },
            {
                "name": "Summarization",
                "order": 90,
                "check": lambda: self._is_enabled(flags, "summarization_enabled", "AGENT_SUMMARIZATION_ENABLED"),
                "flag_key": "summarization_enabled",
                "settings_key": "AGENT_SUMMARIZATION_ENABLED",
                "params": {
                    "trigger_messages": self._get_value(flags, "summarization_trigger_messages", settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES),
                    "keep_messages": self._get_value(flags, "summarization_keep_messages", settings.AGENT_SUMMARIZATION_KEEP_MESSAGES),
                },
            },
            {
                "name": "StrictMode",
                "order": 100,
                "check": lambda: mode == "strict" or self._is_enabled(flags, "strict_mode_enabled", "AGENT_STRICT_MODE_ENABLED"),
                "flag_key": "strict_mode_enabled",
                "settings_key": None,
                "params": {},
            },
        ]

        for mdef in middleware_defs:
            is_enabled = mdef["check"]()
            source = self._get_source(flags, mdef["flag_key"], mdef["settings_key"])
            reason = None if is_enabled else self._get_disable_reason(flags, mdef["flag_key"], mdef["settings_key"])

            info = MiddlewareInfo(
                name=mdef["name"],
                order=mdef["order"],
                enabled=is_enabled,
                source=source,
                reason=reason,
                params=mdef["params"] if is_enabled else {},
            )

            if is_enabled:
                pipeline.append(info)
            elif include_filtered:
                disabled.append(info)

        # 按 order 排序
        pipeline.sort(key=lambda x: x.order)
        disabled.sort(key=lambda x: x.order)

        return EffectiveMiddlewares(pipeline=pipeline, disabled=disabled)

    def _build_knowledge(self, agent: "Agent") -> EffectiveKnowledge:
        """构建知识源信息"""
        if not agent.knowledge_config:
            return EffectiveKnowledge(configured=False)

        kc = agent.knowledge_config
        return EffectiveKnowledge(
            configured=True,
            type=kc.type,
            name=kc.name,
            index_name=kc.index_name,
            collection_name=kc.collection_name,
            embedding_model=kc.embedding_model,
            top_k=kc.top_k,
            similarity_threshold=kc.similarity_threshold,
            rerank_enabled=kc.rerank_enabled,
            data_version=kc.data_version,
        )

    def _build_policies(self, agent: "Agent", mode: str) -> EffectivePolicies:
        """构建策略信息"""
        # 工具策略
        default_policy = DEFAULT_TOOL_POLICIES.get(agent.type, {})
        agent_policy = agent.tool_policy or {}

        tool_policy = EffectiveToolPolicy(
            min_tool_calls=PolicyValue(
                value=agent_policy.get("min_tool_calls", default_policy.get("min_tool_calls", 0)),
                source="agent" if "min_tool_calls" in agent_policy else "default",
            ),
            allow_direct_answer=PolicyValue(
                value=agent_policy.get("allow_direct_answer", default_policy.get("allow_direct_answer", True)),
                source="agent" if "allow_direct_answer" in agent_policy else "default",
            ),
            fallback_tool=PolicyValue(
                value=agent_policy.get("fallback_tool"),
                source="agent",
            ) if "fallback_tool" in agent_policy else None,
            clarification_tool=PolicyValue(
                value=agent_policy.get("clarification_tool"),
                source="agent",
            ) if "clarification_tool" in agent_policy else None,
        )

        # 中间件 Flags
        flags = agent.middleware_flags or {}
        middleware_flags: dict[str, PolicyValue] = {}

        flag_keys = [
            ("todo_enabled", "AGENT_TODO_ENABLED"),
            ("memory_enabled", "MEMORY_ENABLED"),
            ("sliding_window_enabled", "AGENT_SLIDING_WINDOW_ENABLED"),
            ("summarization_enabled", "AGENT_SUMMARIZATION_ENABLED"),
            ("noise_filter_enabled", "AGENT_NOISE_FILTER_ENABLED"),
            ("tool_retry_enabled", "AGENT_TOOL_RETRY_ENABLED"),
            ("strict_mode_enabled", None),
        ]

        for flag_key, settings_key in flag_keys:
            if flag_key in flags and flags[flag_key] is not None:
                middleware_flags[flag_key] = PolicyValue(value=flags[flag_key], source="agent")
            elif settings_key:
                middleware_flags[flag_key] = PolicyValue(
                    value=getattr(settings, settings_key, False),
                    source="settings",
                )
            elif flag_key == "strict_mode_enabled":
                middleware_flags[flag_key] = PolicyValue(
                    value=mode == "strict",
                    source="mode",
                )

        return EffectivePolicies(
            mode=mode,
            tool_policy=tool_policy,
            middleware_flags=middleware_flags,
        )

    def _build_health(
        self,
        system_prompt: EffectiveSystemPrompt,
        skills: EffectiveSkills,
        tools: EffectiveTools,
        middlewares: EffectiveMiddlewares,
        knowledge: EffectiveKnowledge,
    ) -> EffectiveHealth:
        """构建健康度检查"""
        warnings: list[str] = []
        passed: list[str] = []
        score = 100

        # 检查系统提示词
        if system_prompt.char_count > 0:
            passed.append("系统提示词已配置")
        else:
            warnings.append("系统提示词为空")
            score -= 20

        # 检查工具
        if len(tools.enabled) > 0:
            passed.append(f"已启用 {len(tools.enabled)} 个工具")
        else:
            warnings.append("未启用任何工具")
            score -= 15

        # 检查技能
        total_skills = len(skills.always_apply) + len(skills.conditional)
        if total_skills > 0:
            passed.append(f"已配置 {total_skills} 个技能")
        else:
            passed.append("无技能配置（可选）")

        # 检查中间件
        if len(middlewares.pipeline) > 0:
            passed.append(f"已启用 {len(middlewares.pipeline)} 个中间件")

        # 检查知识源（FAQ/KB 类型需要）
        if knowledge.configured:
            passed.append("知识源已配置")
        else:
            passed.append("未配置知识源（可选）")

        return EffectiveHealth(
            score=max(0, score),
            warnings=warnings,
            passed=passed,
        )

    # ========== 辅助方法 ==========

    def _is_enabled(self, flags: Any, flag_key: str | None, settings_key: str | None) -> bool:
        """检查是否启用"""
        if flags and flag_key:
            value = getattr(flags, flag_key, None)
            if value is not None:
                return value
        if settings_key:
            return getattr(settings, settings_key, False)
        return False

    def _get_value(self, flags: Any, flag_key: str, default: Any) -> Any:
        """获取配置值"""
        if flags:
            value = getattr(flags, flag_key, None)
            if value is not None:
                return value
        return default

    def _get_source(self, flags: Any, flag_key: str | None, settings_key: str | None) -> str:
        """获取配置来源"""
        if flags and flag_key:
            value = getattr(flags, flag_key, None)
            if value is not None:
                return f"middleware_flags.{flag_key}"
        if settings_key:
            return f"settings.{settings_key}"
        return "默认启用"

    def _get_disable_reason(self, flags: Any, flag_key: str | None, settings_key: str | None) -> str:
        """获取禁用原因"""
        if flags and flag_key:
            value = getattr(flags, flag_key, None)
            if value is False:
                return f"middleware_flags.{flag_key} = false"
        if settings_key:
            value = getattr(settings, settings_key, None)
            if value is False:
                return f"settings.{settings_key} = false"
        return "未启用"
