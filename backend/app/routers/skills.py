"""技能管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.models.skill import SkillCategory, SkillType
from app.schemas.skill import (
    AgentSkillRead,
    AgentSkillsUpdate,
    SkillCreate,
    SkillGenerateRequest,
    SkillGenerateResponse,
    SkillListResponse,
    SkillRead,
    SkillRefineRequest,
    SkillUpdate,
)
from app.services.skill.generator import SkillGenerator
from app.services.skill.registry import skill_registry
from app.services.skill.service import SkillService
from app.services.skill.system_skills import SYSTEM_SKILLS

logger = get_logger("routers.skills")

router = APIRouter(
    prefix="/api/v1/admin/skills",
    tags=["skills"],
)


# ========== 技能 CRUD ==========


@router.get("", response_model=SkillListResponse)
async def list_skills(
    type: SkillType | None = None,
    category: SkillCategory | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db_session),
):
    """获取技能列表"""
    service = SkillService(db)
    return await service.list_skills(
        skill_type=type,
        category=category,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    data: SkillCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建技能"""
    service = SkillService(db)
    skill = await service.create_skill(data)
    await db.commit()
    await skill_registry.reload()
    return SkillRead.model_validate(skill)


@router.get("/{skill_id}", response_model=SkillRead)
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取技能详情"""
    service = SkillService(db)
    skill = await service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return SkillRead.model_validate(skill)


@router.put("/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: str,
    data: SkillUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新技能（系统技能不可更新）"""
    service = SkillService(db)
    try:
        skill = await service.update_skill(skill_id, data)
        if not skill:
            raise HTTPException(status_code=404, detail="技能不存在")
        await db.commit()
        await skill_registry.reload()
        return SkillRead.model_validate(skill)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除技能（系统技能不可删除）"""
    service = SkillService(db)
    try:
        success = await service.delete_skill(skill_id)
        if not success:
            raise HTTPException(status_code=404, detail="技能不存在")
        await db.commit()
        await skill_registry.reload()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== AI 生成 ==========


@router.post("/generate", response_model=SkillGenerateResponse)
async def generate_skill(data: SkillGenerateRequest):
    """AI 生成技能（不需要数据库）"""
    generator = SkillGenerator()
    try:
        return await generator.generate(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{skill_id}/refine", response_model=SkillGenerateResponse)
async def refine_skill(
    skill_id: str,
    data: SkillRefineRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """AI 优化技能"""
    service = SkillService(db)
    skill = await service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    # 转换为字典
    skill_data = {
        "name": skill.name,
        "description": skill.description,
        "category": skill.category.value,
        "content": skill.content,
        "trigger_keywords": skill.trigger_keywords,
        "trigger_intents": skill.trigger_intents,
        "always_apply": skill.always_apply,
        "applicable_agents": skill.applicable_agents,
    }

    generator = SkillGenerator()
    try:
        return await generator.refine(skill_data, data.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== Agent 技能配置 ==========


@router.get("/agents/{agent_id}", response_model=list[AgentSkillRead])
async def get_agent_skills(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 的技能列表"""
    service = SkillService(db)
    return await service.get_skills_for_agent(agent_id, include_disabled=True)


@router.put("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_agent_skills(
    agent_id: str,
    data: AgentSkillsUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 Agent 的技能配置"""
    service = SkillService(db)
    await service.update_agent_skills(agent_id, data.skills)
    await db.commit()


# ========== 系统技能 ==========


@router.get("/system/list", response_model=list[SkillRead])
async def get_system_skills(
    db: AsyncSession = Depends(get_db_session),
):
    """获取系统内置技能"""
    service = SkillService(db)
    skills = await service.get_system_skills()
    return [SkillRead.model_validate(s) for s in skills]


@router.post("/system/init", status_code=status.HTTP_200_OK)
async def init_system_skills(
    db: AsyncSession = Depends(get_db_session),
):
    """初始化系统内置技能"""
    service = SkillService(db)
    count = await service.init_system_skills(SYSTEM_SKILLS)
    await db.commit()
    await skill_registry.reload()
    return {"message": f"初始化完成，新增 {count} 个技能", "created": count}


# ========== 缓存管理 ==========


@router.post("/cache/reload", status_code=status.HTTP_204_NO_CONTENT)
async def reload_skill_cache():
    """重新加载技能缓存"""
    await skill_registry.reload()


@router.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_skill_cache():
    """清除技能缓存"""
    skill_registry.invalidate()
