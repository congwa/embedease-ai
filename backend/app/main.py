"""FastAPI 应用入口"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import logger
from app.core.models_dev import get_model_profile
from app.routers import chat, conversations, users
from app.services.agent.agent import agent_service


def _init_model_profiles() -> None:
    """启动时初始化模型配置（拉取 models.dev 并打印）"""
    model_name = settings.SILICONFLOW_CHAT_MODEL

    if settings.MODELS_DEV_ENABLED:
        logger.info(
            "正在从 models.dev 获取模型配置...",
            module="app",
            model=model_name,
            provider=settings.MODELS_DEV_PROVIDER_ID,
            api_url=settings.MODELS_DEV_API_URL,
        )
        profile = get_model_profile(
            model_name=model_name,
            api_url=settings.MODELS_DEV_API_URL,
            provider_id=settings.MODELS_DEV_PROVIDER_ID,
            timeout_seconds=settings.MODELS_DEV_TIMEOUT_SECONDS,
            cache_ttl_seconds=settings.MODELS_DEV_CACHE_TTL_SECONDS,
            env_profiles=settings.siliconflow_model_profiles,
        )
    else:
        model_key = model_name.strip().lower()
        profile = settings.siliconflow_model_profiles.get(model_key, {})
        logger.info(
            "models.dev 已禁用，使用 .env 配置",
            module="app",
            model=model_name,
        )

    # 打印最终生效的模型配置
    logger.info(
        "模型配置已加载",
        module="app",
        model=model_name,
        profile=profile,
        reasoning_output=profile.get("reasoning_output"),
        tool_calling=profile.get("tool_calling"),
        structured_output=profile.get("structured_output"),
        max_input_tokens=profile.get("max_input_tokens"),
        max_output_tokens=profile.get("max_output_tokens"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时配置日志（确保最先执行）
    logger.configure()
    
    logger.info("启动应用...", module="app")
    settings.ensure_data_dir()

    # 初始化模型配置（拉取 models.dev）
    _init_model_profiles()

    await init_db()
    logger.info("应用启动完成", module="app", host=settings.API_HOST, port=settings.API_PORT)
    
    yield
    
    logger.info("正在关闭应用...", module="app")
    await agent_service.close()
    logger.info("应用已关闭", module="app")


app = FastAPI(
    title="商品推荐 Agent",
    description="基于 LangChain v1.1 的智能商品推荐系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(users.router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
