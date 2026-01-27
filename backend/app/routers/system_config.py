"""系统配置 API 路由

提供 LLM、Embedding、Rerank 等配置的管理接口。
支持快速配置（只需 API Key）和完整配置两种模式。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.schemas.system_config import (
    AvailableAgentForSupervisor,
    ConfigTestRequest,
    ConfigTestResponse,
    FullConfigUpdate,
    ProviderPresetsResponse,
    QuickConfigUpdate,
    SupervisorGlobalConfigResponse,
    SupervisorGlobalConfigUpdate,
    SupervisorSubAgent,
    SystemConfigReadMasked,
)
from app.services.system_config import SupervisorGlobalConfigService, SystemConfigService

router = APIRouter(prefix="/api/v1/admin/system-config", tags=["system-config"])
logger = get_logger("routers.system_config")


@router.get("", response_model=SystemConfigReadMasked)
async def get_system_config(db: AsyncSession = Depends(get_db_session)):
    """获取系统配置（API Key 脱敏）"""
    service = SystemConfigService(db)
    return await service.get_config_masked()


@router.get("/providers", response_model=ProviderPresetsResponse)
async def get_provider_presets(db: AsyncSession = Depends(get_db_session)):
    """获取提供商预设列表"""
    service = SystemConfigService(db)
    return service.get_provider_presets()


@router.post("/quick", response_model=SystemConfigReadMasked)
async def update_quick_config(
    data: QuickConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """快速配置（只需 API Key）

    自动使用提供商的默认配置，适合快速开始。
    """
    service = SystemConfigService(db)
    result = await service.update_quick_config(data)
    logger.info("快速配置已更新", provider=data.provider)
    return result


@router.post("/full", response_model=SystemConfigReadMasked)
async def update_full_config(
    data: FullConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """完整配置更新

    允许自定义所有配置项，适合高级用户。
    """
    service = SystemConfigService(db)
    result = await service.update_full_config(data)
    logger.info(
        "完整配置已更新",
        llm_provider=data.llm_provider,
        embedding_provider=data.embedding_provider,
    )
    return result


@router.post("/test", response_model=ConfigTestResponse)
async def test_config(
    data: ConfigTestRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """测试配置是否可用

    在保存前测试 API Key 和 Base URL 是否正确。
    """
    service = SystemConfigService(db)
    return await service.test_config(data)


@router.get("/status")
async def get_config_status(db: AsyncSession = Depends(get_db_session)):
    """获取配置状态

    用于检查系统是否已配置，是否可以正常使用。
    """
    service = SystemConfigService(db)
    is_configured = await service.is_configured()
    config = await service.get_config_masked()

    return {
        "configured": is_configured,
        "source": config.source,
        "llm_provider": config.llm_provider if is_configured else None,
        "embedding_model": config.embedding_model if is_configured else None,
    }


# ========== Supervisor 全局配置 ==========


@router.get("/supervisor", response_model=SupervisorGlobalConfigResponse)
async def get_supervisor_config(db: AsyncSession = Depends(get_db_session)):
    """获取全局 Supervisor 配置

    返回当前生效的 Supervisor 配置，优先从数据库读取，其次从环境变量。
    """
    service = SupervisorGlobalConfigService(db)
    return await service.get_config()


@router.post("/supervisor", response_model=SupervisorGlobalConfigResponse)
async def update_supervisor_config(
    data: SupervisorGlobalConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新全局 Supervisor 配置

    支持部分更新，未提供的字段保持原值。
    更新后立即生效，无需重启服务。
    """
    service = SupervisorGlobalConfigService(db)
    result = await service.update_config(data)
    logger.info(
        "Supervisor 全局配置已更新",
        enabled=result.enabled,
        sub_agent_count=len(result.sub_agents),
    )
    return result


@router.get("/supervisor/available-agents", response_model=list[AvailableAgentForSupervisor])
async def get_available_agents_for_supervisor(db: AsyncSession = Depends(get_db_session)):
    """获取可选为子 Agent 的 Agent 列表

    返回所有启用的 Agent，标记哪些已被选为子 Agent。
    """
    service = SupervisorGlobalConfigService(db)
    return await service.get_available_agents()


class AddSubAgentRequest(SupervisorSubAgent):
    """添加子 Agent 请求"""
    pass


@router.post("/supervisor/sub-agents", response_model=SupervisorGlobalConfigResponse)
async def add_sub_agent(
    data: AddSubAgentRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """添加子 Agent"""
    service = SupervisorGlobalConfigService(db)
    return await service.add_sub_agent(
        agent_id=data.agent_id,
        name=data.name,
        description=data.description,
        routing_hints=data.routing_hints,
        priority=data.priority,
    )


@router.delete("/supervisor/sub-agents/{agent_id}", response_model=SupervisorGlobalConfigResponse)
async def remove_sub_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """移除子 Agent"""
    service = SupervisorGlobalConfigService(db)
    return await service.remove_sub_agent(agent_id)
