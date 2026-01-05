"""Agent 服务模块

多 Agent 架构目录结构：
├── core/           # 核心基础设施
│   ├── service.py  # AgentService（按 agent_id + mode 缓存）
│   ├── config.py   # AgentConfigLoader
│   ├── factory.py  # Agent 工厂
│   └── policy.py   # 策略
├── retrieval/      # 检索器
│   ├── product.py  # 商品检索
│   └── enhanced.py # 增强检索
├── middleware/     # 中间件
├── streams/        # 流处理
└── tools/          # 工具（按业务分组）
    ├── registry.py # 工具注册表
    ├── product/    # 商品工具
    ├── knowledge/  # 知识库工具
    └── common/     # 通用工具
"""

from app.services.agent.core import (
    AgentConfigLoader,
    AgentService,
    agent_service,
    get_or_create_default_agent,
)
from app.services.agent.retrieval import get_retriever
from app.services.agent.tools.product import search_products

__all__ = [
    "AgentConfigLoader",
    "AgentService",
    "agent_service",
    "get_or_create_default_agent",
    "get_retriever",
    "search_products",
]
