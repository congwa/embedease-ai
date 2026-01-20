"""意图分类器

用于 Supervisor 模式下的用户意图识别和 Agent 路由。
"""

import re
from typing import Any

from app.core.config import settings
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.schemas.agent import RoutingPolicy, RoutingRule, SubAgentConfig

logger = get_logger("agent.intent")


class IntentClassifier:
    """意图分类器

    根据路由策略分析用户消息，返回应该路由到的目标 Agent。
    支持三种策略：
    - keyword: 关键词匹配
    - intent: LLM 意图识别
    - hybrid: 先关键词，再意图
    """

    def __init__(
        self,
        routing_policy: RoutingPolicy,
        sub_agents: list[SubAgentConfig],
    ):
        self.policy = routing_policy
        self.sub_agents = sub_agents
        self._agent_map = {sa.agent_id: sa for sa in sub_agents}

    async def classify(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """分类用户意图，返回目标 Agent ID

        Args:
            message: 用户消息
            context: 上下文信息（如历史消息、当前 Agent 等）

        Returns:
            目标 Agent ID 或 None（使用默认）
        """
        context = context or {}

        # 1. 检查上下文延续（如果当前有 Agent 在处理，可能继续使用）
        current_agent = context.get("current_agent")
        if current_agent and self._should_continue(message, current_agent):
            logger.debug(f"上下文延续，继续使用 Agent: {current_agent}")
            return current_agent

        # 2. 根据策略类型进行路由
        if self.policy.type == "keyword":
            return await self._keyword_routing(message)
        elif self.policy.type == "intent":
            return await self._intent_routing(message, context)
        else:  # hybrid
            # 先尝试关键词匹配
            result = await self._keyword_routing(message)
            if result:
                return result
            # 再尝试 LLM 意图识别
            return await self._intent_routing(message, context)

    async def _keyword_routing(self, message: str) -> str | None:
        """关键词匹配路由"""
        message_lower = message.lower()

        # 1. 先检查路由规则中的关键词
        keyword_rules = [
            r for r in self.policy.rules
            if r.condition.type == "keyword" and r.condition.keywords
        ]
        # 按优先级排序
        keyword_rules.sort(key=lambda r: r.priority, reverse=True)

        for rule in keyword_rules:
            for keyword in rule.condition.keywords or []:
                if keyword.lower() in message_lower:
                    logger.debug(
                        f"关键词匹配成功",
                        keyword=keyword,
                        target=rule.target,
                    )
                    return rule.target

        # 2. 检查子 Agent 的 routing_hints
        for sub_agent in sorted(self.sub_agents, key=lambda x: x.priority, reverse=True):
            for hint in sub_agent.routing_hints:
                if hint.lower() in message_lower:
                    logger.debug(
                        f"routing_hints 匹配成功",
                        hint=hint,
                        target=sub_agent.agent_id,
                    )
                    return sub_agent.agent_id

        return None

    async def _intent_routing(
        self,
        message: str,
        context: dict[str, Any],
    ) -> str | None:
        """LLM 意图识别路由"""
        if not settings.SUPERVISOR_ENABLED:
            return self.policy.default_agent

        try:
            # 构建意图分类提示词
            prompt = self._build_intent_prompt(message)

            # 调用 LLM
            model = get_chat_model()
            response = await model.ainvoke(prompt)

            # 解析响应
            intent = self._parse_intent_response(response.content)
            if intent:
                target = self._match_intent_to_agent(intent)
                if target:
                    logger.debug(
                        f"意图识别成功",
                        intent=intent,
                        target=target,
                    )
                    return target

        except Exception as e:
            logger.warning(f"意图识别失败: {e}")

        return self.policy.default_agent

    def _build_intent_prompt(self, message: str) -> str:
        """构建意图分类提示词"""
        # 收集可用意图
        available_intents = set()
        for rule in self.policy.rules:
            if rule.condition.type == "intent" and rule.condition.intents:
                available_intents.update(rule.condition.intents)

        # 添加子 Agent 描述作为候选
        agent_descriptions = []
        for sa in self.sub_agents:
            desc = f"- {sa.name}: {sa.description or ''}"
            if sa.routing_hints:
                desc += f" (相关: {', '.join(sa.routing_hints)})"
            agent_descriptions.append(desc)

        prompt = f"""分析以下用户消息的意图，从给定的候选意图中选择最匹配的一个。

用户消息: {message}

可选意图:
{chr(10).join(f'- {intent}' for intent in available_intents) if available_intents else '无预定义意图'}

可用助手:
{chr(10).join(agent_descriptions)}

请只输出一个意图标识或助手名称，不要输出其他内容。
如果无法确定，输出: unknown
"""
        return prompt

    def _parse_intent_response(self, response: str) -> str | None:
        """解析 LLM 意图响应"""
        if not response:
            return None

        # 清理响应
        intent = response.strip().lower()
        intent = re.sub(r'^[\-\*\s]+', '', intent)  # 移除列表符号
        intent = intent.split('\n')[0]  # 只取第一行

        if intent == "unknown":
            return None

        return intent

    def _match_intent_to_agent(self, intent: str) -> str | None:
        """将意图映射到 Agent ID"""
        # 1. 检查意图规则
        for rule in self.policy.rules:
            if rule.condition.type == "intent" and rule.condition.intents:
                for rule_intent in rule.condition.intents:
                    if rule_intent.lower() == intent or intent in rule_intent.lower():
                        return rule.target

        # 2. 检查子 Agent 名称匹配
        for sa in self.sub_agents:
            if sa.name.lower() in intent or intent in sa.name.lower():
                return sa.agent_id

        return None

    def _should_continue(self, message: str, current_agent: str) -> bool:
        """判断是否应该继续使用当前 Agent"""
        # 简单逻辑：如果消息很短（追问），继续使用当前 Agent
        if len(message) < 20:
            return True

        # 检查是否有明确的切换信号
        switch_signals = ["换一个", "换个", "其他", "另一个", "不是这个"]
        for signal in switch_signals:
            if signal in message:
                return False

        return False

    def get_default_agent(self) -> str | None:
        """获取默认 Agent ID"""
        if self.policy.default_agent:
            return self.policy.default_agent

        # 返回优先级最高的子 Agent
        if self.sub_agents:
            return max(self.sub_agents, key=lambda x: x.priority).agent_id

        return None
