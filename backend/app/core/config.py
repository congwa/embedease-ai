"""应用配置管理"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 硅基流动配置（必填，无默认值 - 必须在 .env 中配置）
    SILICONFLOW_API_KEY: str  # API Key（必填）
    SILICONFLOW_BASE_URL: str  # API Base URL（必填，如 https://api.siliconflow.cn/v1）
    SILICONFLOW_CHAT_MODEL: str  # 聊天模型 ID（必填，如 moonshotai/Kimi-K2-Instruct）
    SILICONFLOW_EMBEDDING_MODEL: str  # 嵌入模型 ID（必填，如 BAAI/bge-m3）
    SILICONFLOW_EMBEDDING_DIMENSION: int  # 嵌入维度（必填，如 4096）
    # 通过 .env 提供 JSON，手动指定第三方/国产模型能力（会覆盖 models.dev 的配置）
    # 示例：
    # SILICONFLOW_MODEL_PROFILES_JSON='{
    #   "moonshotai/Kimi-K2-Thinking": {"reasoning_output": true, "tool_calling": true, "structured_output": true}
    # }'
    SILICONFLOW_MODEL_PROFILES_JSON: str = ""

    # models.dev 配置（开源模型能力数据库）
    # 启动时会自动拉取 https://models.dev/api.json 获取模型能力配置
    # 合并规则：models.dev 作为基础，SILICONFLOW_MODEL_PROFILES_JSON 作为强覆盖（env 优先）
    MODELS_DEV_ENABLED: bool = True  # 是否启用 models.dev 自动拉取
    MODELS_DEV_API_URL: str = "https://models.dev/api.json"  # API URL
    MODELS_DEV_PROVIDER_ID: str = "siliconflow"  # provider ID（对应 api.json 中的顶层 key）
    MODELS_DEV_TIMEOUT_SECONDS: float = 10.0  # 请求超时时间
    MODELS_DEV_CACHE_TTL_SECONDS: float = 86400.0  # 缓存 TTL（秒），0 表示每次都拉取

    # Qdrant 配置
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "products"

    # 数据库配置
    DATABASE_PATH: str = "./data/app.db"
    CHECKPOINT_DB_PATH: str = "./data/checkpoints.db"

    # 文本处理配置
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100

    # 服务配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"

    # 日志配置
    LOG_LEVEL: str = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_MODE: str = "detailed"  # simple, detailed, json
    LOG_FILE: str = "./logs/app.log"  # 日志文件路径，留空则不记录文件
    LOG_FILE_ROTATION: str = "10 MB"  # 日志文件轮转大小
    LOG_FILE_RETENTION: str = "7 days"  # 日志文件保留时间

    @property
    def database_url(self) -> str:
        """SQLite 数据库 URL"""
        return f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS 允许的源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        Path(self.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.CHECKPOINT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    @property
    def siliconflow_model_profiles(self) -> dict[str, dict[str, Any]]:
        """解析 .env 中的模型 profile JSON 配置。"""
        raw = (self.SILICONFLOW_MODEL_PROFILES_JSON or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            # 环境变量属于系统边界：允许报错并提示用户修正配置
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for k, v in parsed.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            out[k.strip().lower()] = v
        return out


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
