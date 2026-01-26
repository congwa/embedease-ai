"""提示词管理 API

提供提示词的 CRUD 操作接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.prompts.registry import PromptRegistry
from app.prompts.schemas import (
    PromptCreate,
    PromptListResponse,
    PromptResetResponse,
    PromptResponse,
    PromptUpdate,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=PromptListResponse)
async def list_prompts(
    category: str | None = Query(None, description="过滤分类：agent/memory/skill/crawler"),
    include_inactive: bool = Query(False, description="是否包含禁用的提示词"),
    session: AsyncSession = Depends(get_session),
):
    """获取所有提示词列表

    返回所有提示词，包括默认值和自定义值。
    自定义值会标记 source=custom 并附带 default_content。
    """
    registry = PromptRegistry(session)
    items = await registry.list_all(category=category, include_inactive=include_inactive)
    return PromptListResponse(items=items, total=len(items))


@router.get("/{key:path}", response_model=PromptResponse)
async def get_prompt(
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """获取单个提示词

    优先返回数据库中的自定义值，无则返回默认值。
    """
    registry = PromptRegistry(session)
    prompt = await registry.get(key)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"提示词 {key} 不存在")
    return prompt


@router.put("/{key:path}", response_model=PromptResponse)
async def update_prompt(
    key: str,
    data: PromptUpdate,
    session: AsyncSession = Depends(get_session),
):
    """更新提示词

    如果数据库无记录，会基于默认值创建新的自定义记录。
    """
    registry = PromptRegistry(session)
    try:
        prompt = await registry.update(key, data)
        await session.commit()
        return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=PromptResponse)
async def create_prompt(
    data: PromptCreate,
    session: AsyncSession = Depends(get_session),
):
    """创建新的自定义提示词

    用于创建不在默认值中的全新提示词。
    """
    registry = PromptRegistry(session)
    try:
        prompt = await registry.create(data)
        await session.commit()
        return prompt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{key:path}/reset", response_model=PromptResetResponse)
async def reset_prompt(
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """重置提示词为默认值

    删除数据库中的自定义记录，恢复使用默认值。
    """
    registry = PromptRegistry(session)
    try:
        prompt = await registry.reset(key)
        await session.commit()
        return PromptResetResponse(
            key=key,
            message="已重置为默认值",
            content=prompt.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{key:path}")
async def delete_prompt(
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """删除自定义提示词

    仅能删除非默认提示词。有默认值的提示词请使用 reset。
    """
    registry = PromptRegistry(session)
    try:
        deleted = await registry.delete(key)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"提示词 {key} 不存在")
        await session.commit()
        return {"message": f"已删除提示词 {key}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
