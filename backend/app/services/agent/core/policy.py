"""工具调用策略配置

定义不同聊天模式下的工具调用策略，替代硬编码的提示词约束。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolPolicy:
    """工具调用策略配置"""

    # 最小工具调用次数（0 表示不强制）
    min_tool_calls: int = 0

    # 无工具调用时的默认回退工具（可选）
    fallback_tool: Optional[str] = None

    # 是否允许无工具调用的直接回答
    allow_direct_answer: bool = True

    # 信息不足时优先使用的澄清工具
    clarification_tool: Optional[str] = None

    # 策略描述（用于日志和调试）
    description: str = ""


# 预定义的策略
NATURAL_POLICY = ToolPolicy(
    min_tool_calls=0, allow_direct_answer=True, description="自然模式：不强制工具调用，允许自由对话"
)

FREE_POLICY = ToolPolicy(
    min_tool_calls=0, allow_direct_answer=True, description="自由模式：完全自由对话，不使用工具"
)

STRICT_POLICY = ToolPolicy(
    min_tool_calls=1,
    fallback_tool="guide_user",
    allow_direct_answer=False,
    clarification_tool="guide_user",
    description="严格模式：必须调用工具，无工具时使用 guide_user",
)


def get_policy(mode: str) -> ToolPolicy:
    """根据聊天模式获取对应的工具策略"""
    policies = {
        "natural": NATURAL_POLICY,
        "free": FREE_POLICY,
        "strict": STRICT_POLICY,
    }
    return policies.get(mode, NATURAL_POLICY)
