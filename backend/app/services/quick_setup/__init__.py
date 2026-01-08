"""Quick Setup 服务模块

提供快捷配置向导的核心功能，包括：
- Agent 类型配置器（多态架构）
- Setup 状态管理
- 配置检查清单
"""

from app.services.quick_setup.configurators import (
    AgentTypeConfigurator,
    CustomAgentConfigurator,
    FAQAgentConfigurator,
    KBAgentConfigurator,
    ProductAgentConfigurator,
    get_configurator,
    get_all_configurators,
)
from app.services.quick_setup.state_manager import QuickSetupStateManager
from app.services.quick_setup.checklist import ChecklistService

__all__ = [
    "AgentTypeConfigurator",
    "ProductAgentConfigurator",
    "FAQAgentConfigurator",
    "KBAgentConfigurator",
    "CustomAgentConfigurator",
    "get_configurator",
    "get_all_configurators",
    "QuickSetupStateManager",
    "ChecklistService",
]
