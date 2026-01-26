"""提示词注册表

核心服务：统一管理所有提示词，支持默认值 + 数据库覆盖。
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt, PromptCategory
from app.prompts.defaults import DEFAULT_PROMPTS
from app.prompts.schemas import (
    PromptCreate,
    PromptResponse,
    PromptSource,
    PromptUpdate,
)

logger = structlog.get_logger(__name__)


class PromptRegistry:
    """提示词注册表

    提供统一的提示词访问接口：
    - get(): 获取单个提示词（优先数据库，fallback 默认值）
    - get_content(): 直接获取提示词内容字符串
    - list_all(): 列出所有提示词
    - update(): 更新/创建自定义提示词
    - reset(): 重置为默认值
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, key: str) -> PromptResponse | None:
        """获取提示词

        优先返回数据库中的自定义值，无则返回默认值。

        Args:
            key: 提示词标识，如 "agent.product"

        Returns:
            PromptResponse 或 None（key 不存在）
        """
        # 1. 查询数据库
        db_prompt = await self._get_from_db(key)

        # 2. 获取默认值
        default = DEFAULT_PROMPTS.get(key)

        if db_prompt:
            # 数据库有记录，返回自定义值
            return PromptResponse(
                key=db_prompt.key,
                category=db_prompt.category.value,
                name=db_prompt.name,
                description=db_prompt.description,
                content=db_prompt.content,
                variables=db_prompt.variables or [],
                source=PromptSource.CUSTOM,
                is_active=db_prompt.is_active,
                default_content=default["content"] if default else None,
                created_at=db_prompt.created_at,
                updated_at=db_prompt.updated_at,
            )
        elif default:
            # 无数据库记录，返回默认值
            return PromptResponse(
                key=key,
                category=default["category"],
                name=default["name"],
                description=default.get("description"),
                content=default["content"],
                variables=default.get("variables", []),
                source=PromptSource.DEFAULT,
                is_active=True,
                default_content=None,
                created_at=None,
                updated_at=None,
            )

        return None

    async def get_content(self, key: str, **kwargs) -> str | None:
        """获取提示词内容字符串

        如果提示词包含变量，可通过 kwargs 传入进行格式化。

        Args:
            key: 提示词标识
            **kwargs: 模板变量

        Returns:
            格式化后的提示词内容，或 None
        """
        prompt = await self.get(key)
        if not prompt:
            return None

        content = prompt.content

        # 如果有变量，进行格式化
        if kwargs and prompt.variables:
            try:
                content = content.format(**kwargs)
            except KeyError as e:
                logger.warning("提示词格式化失败", key=key, missing_var=str(e))

        return content

    async def list_all(
        self,
        category: str | None = None,
        include_inactive: bool = False,
    ) -> list[PromptResponse]:
        """列出所有提示词

        Args:
            category: 过滤分类
            include_inactive: 是否包含禁用的提示词

        Returns:
            提示词列表
        """
        result: list[PromptResponse] = []

        # 1. 获取数据库中的自定义提示词
        stmt = select(Prompt)
        if category:
            stmt = stmt.where(Prompt.category == category)
        if not include_inactive:
            stmt = stmt.where(Prompt.is_active == True)  # noqa: E712

        db_result = await self._session.execute(stmt)
        db_prompts = {p.key: p for p in db_result.scalars().all()}

        # 2. 合并默认值和数据库值
        for key, default in DEFAULT_PROMPTS.items():
            # 过滤分类
            if category and default["category"] != category:
                continue

            if key in db_prompts:
                # 数据库有覆盖
                db_prompt = db_prompts[key]
                if not include_inactive and not db_prompt.is_active:
                    continue
                result.append(
                    PromptResponse(
                        key=key,
                        category=db_prompt.category.value,
                        name=db_prompt.name,
                        description=db_prompt.description,
                        content=db_prompt.content,
                        variables=db_prompt.variables or [],
                        source=PromptSource.CUSTOM,
                        is_active=db_prompt.is_active,
                        default_content=default["content"],
                        created_at=db_prompt.created_at,
                        updated_at=db_prompt.updated_at,
                    )
                )
            else:
                # 使用默认值
                result.append(
                    PromptResponse(
                        key=key,
                        category=default["category"],
                        name=default["name"],
                        description=default.get("description"),
                        content=default["content"],
                        variables=default.get("variables", []),
                        source=PromptSource.DEFAULT,
                        is_active=True,
                        default_content=None,
                        created_at=None,
                        updated_at=None,
                    )
                )

        # 3. 添加数据库中但不在默认值中的自定义提示词
        for key, db_prompt in db_prompts.items():
            if key not in DEFAULT_PROMPTS:
                if category and db_prompt.category.value != category:
                    continue
                if not include_inactive and not db_prompt.is_active:
                    continue
                result.append(
                    PromptResponse(
                        key=key,
                        category=db_prompt.category.value,
                        name=db_prompt.name,
                        description=db_prompt.description,
                        content=db_prompt.content,
                        variables=db_prompt.variables or [],
                        source=PromptSource.CUSTOM,
                        is_active=db_prompt.is_active,
                        default_content=None,
                        created_at=db_prompt.created_at,
                        updated_at=db_prompt.updated_at,
                    )
                )

        # 按 key 排序
        result.sort(key=lambda p: p.key)
        return result

    async def update(self, key: str, data: PromptUpdate) -> PromptResponse:
        """更新提示词

        如果数据库无记录，基于默认值创建新记录。

        Args:
            key: 提示词标识
            data: 更新数据

        Returns:
            更新后的 PromptResponse
        """
        db_prompt = await self._get_from_db(key)
        default = DEFAULT_PROMPTS.get(key)

        if db_prompt:
            # 更新现有记录
            if data.name is not None:
                db_prompt.name = data.name
            if data.description is not None:
                db_prompt.description = data.description
            if data.content is not None:
                db_prompt.content = data.content
            if data.is_active is not None:
                db_prompt.is_active = data.is_active

            await self._session.flush()
            logger.info("更新提示词", key=key)

        else:
            # 创建新记录
            if not default:
                raise ValueError(f"提示词 {key} 不存在")

            db_prompt = Prompt(
                key=key,
                category=PromptCategory(default["category"]),
                name=data.name or default["name"],
                description=data.description or default.get("description"),
                content=data.content or default["content"],
                variables=default.get("variables", []),
                is_active=data.is_active if data.is_active is not None else True,
            )
            self._session.add(db_prompt)
            await self._session.flush()
            logger.info("创建自定义提示词", key=key)

        return PromptResponse(
            key=db_prompt.key,
            category=db_prompt.category.value,
            name=db_prompt.name,
            description=db_prompt.description,
            content=db_prompt.content,
            variables=db_prompt.variables or [],
            source=PromptSource.CUSTOM,
            is_active=db_prompt.is_active,
            default_content=default["content"] if default else None,
            created_at=db_prompt.created_at,
            updated_at=db_prompt.updated_at,
        )

    async def create(self, data: PromptCreate) -> PromptResponse:
        """创建新的自定义提示词

        Args:
            data: 创建数据

        Returns:
            创建的 PromptResponse
        """
        # 检查是否已存在
        existing = await self._get_from_db(data.key)
        if existing:
            raise ValueError(f"提示词 {data.key} 已存在")

        db_prompt = Prompt(
            key=data.key,
            category=PromptCategory(data.category),
            name=data.name,
            description=data.description,
            content=data.content,
            variables=data.variables,
            is_active=True,
        )
        self._session.add(db_prompt)
        await self._session.flush()

        logger.info("创建自定义提示词", key=data.key)

        return PromptResponse(
            key=db_prompt.key,
            category=db_prompt.category.value,
            name=db_prompt.name,
            description=db_prompt.description,
            content=db_prompt.content,
            variables=db_prompt.variables or [],
            source=PromptSource.CUSTOM,
            is_active=db_prompt.is_active,
            default_content=None,
            created_at=db_prompt.created_at,
            updated_at=db_prompt.updated_at,
        )

    async def reset(self, key: str) -> PromptResponse:
        """重置提示词为默认值

        删除数据库中的自定义记录。

        Args:
            key: 提示词标识

        Returns:
            重置后的 PromptResponse（默认值）
        """
        default = DEFAULT_PROMPTS.get(key)
        if not default:
            raise ValueError(f"提示词 {key} 无默认值，无法重置")

        # 删除数据库记录
        db_prompt = await self._get_from_db(key)
        if db_prompt:
            await self._session.delete(db_prompt)
            await self._session.flush()
            logger.info("重置提示词为默认值", key=key)

        return PromptResponse(
            key=key,
            category=default["category"],
            name=default["name"],
            description=default.get("description"),
            content=default["content"],
            variables=default.get("variables", []),
            source=PromptSource.DEFAULT,
            is_active=True,
            default_content=None,
            created_at=None,
            updated_at=None,
        )

    async def delete(self, key: str) -> bool:
        """删除自定义提示词

        仅能删除非默认提示词。

        Args:
            key: 提示词标识

        Returns:
            是否成功删除
        """
        if key in DEFAULT_PROMPTS:
            raise ValueError(f"提示词 {key} 有默认值，请使用 reset 重置")

        db_prompt = await self._get_from_db(key)
        if not db_prompt:
            return False

        await self._session.delete(db_prompt)
        await self._session.flush()
        logger.info("删除自定义提示词", key=key)
        return True

    async def _get_from_db(self, key: str) -> Prompt | None:
        """从数据库获取提示词"""
        stmt = select(Prompt).where(Prompt.key == key)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# ========== 便捷函数 ==========


async def get_prompt_content(
    session: AsyncSession,
    key: str,
    **kwargs,
) -> str | None:
    """便捷函数：获取提示词内容

    Args:
        session: 数据库会话
        key: 提示词标识
        **kwargs: 模板变量

    Returns:
        格式化后的提示词内容
    """
    registry = PromptRegistry(session)
    return await registry.get_content(key, **kwargs)


def get_default_prompt_content(key: str, **kwargs) -> str | None:
    """便捷函数：获取默认提示词内容（不查询数据库）

    Args:
        key: 提示词标识
        **kwargs: 模板变量

    Returns:
        格式化后的提示词内容
    """
    default = DEFAULT_PROMPTS.get(key)
    if not default:
        return None

    content = default["content"]
    if kwargs:
        try:
            content = content.format(**kwargs)
        except KeyError:
            pass

    return content
