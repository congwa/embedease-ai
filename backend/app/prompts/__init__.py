"""提示词统一管理模块

提供集中式的提示词管理，支持：
- 代码级默认值定义
- 数据库存储自定义值
- 后台管理界面 CRUD
"""

from app.prompts.registry import PromptRegistry

__all__ = ["PromptRegistry"]
