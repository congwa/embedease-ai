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

    # ========== LLM 提供商配置 ==========
    # 主要提供商设置
    LLM_PROVIDER: str = "siliconflow"  # 提供商: openai, openrouter, siliconflow 等
    LLM_API_KEY: str  # API Key（必填）
    LLM_BASE_URL: str  # API Base URL（必填）
    LLM_CHAT_MODEL: str  # 聊天模型 ID（必填）

    # ========== Embeddings 配置 ==========
    # Embeddings 提供商设置（可以与 LLM 不同）
    EMBEDDING_PROVIDER: str = "siliconflow"  # Embedding 提供商
    EMBEDDING_API_KEY: str | None = None  # 如为空则使用 LLM_API_KEY
    EMBEDDING_BASE_URL: str | None = None  # 如为空则使用 LLM_BASE_URL
    EMBEDDING_MODEL: str  # 嵌入模型 ID（必填）
    EMBEDDING_DIMENSION: int  # 嵌入维度（必填）

    # ========== Rerank 配置 ==========
    RERANK_ENABLED: bool = False  # 是否启用 Rerank 重排序
    RERANK_PROVIDER: str | None = None  # Rerank 提供商（可选，默认使用 LLM_PROVIDER）
    RERANK_API_KEY: str | None = None  # 如为空则使用 LLM_API_KEY
    RERANK_BASE_URL: str | None = None  # 如为空则使用 LLM_BASE_URL
    RERANK_MODEL: str | None = None  # Rerank 模型 ID
    RERANK_TOP_N: int = 5  # 返回前 N 个结果
    RERANK_INSTRUCTION: str = "根据查询对商品进行相关性排序"  # Rerank 指令

    # ========== 模型能力配置 ==========
    # 通过 .env 提供 JSON，手动指定模型能力（会覆盖 models.dev 的配置）
    # 示例：
    # MODEL_PROFILES_JSON='{
    #   "moonshotai/Kimi-K2-Thinking": {"reasoning_output": true, "tool_calling": true, "structured_output": true}
    # }'
    MODEL_PROFILES_JSON: str = ""

    # models.dev 配置（开源模型能力数据库）
    # 启动时会自动拉取 https://models.dev/api.json 获取模型能力配置
    # 合并规则：models.dev 作为基础，MODEL_PROFILES_JSON 作为强覆盖（env 优先）
    MODELS_DEV_ENABLED: bool = True  # 是否启用 models.dev 自动拉取
    MODELS_DEV_API_URL: str = "https://models.dev/api.json"  # API URL
    MODELS_DEV_PROVIDER_ID: str | None = None  # provider ID（对应 api.json 中的顶层 key，默认使用 LLM_PROVIDER）
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

    # ========== 响应清洗配置 ==========
    RESPONSE_SANITIZATION_ENABLED: bool = True  # 是否启用响应清洗（检测并替换异常 function call 格式）
    RESPONSE_SANITIZATION_CUSTOM_MESSAGE: str | None = None  # 自定义降级消息（可选，留空使用默认消息）

    # ========== 聊天模式配置 ==========
    # natural: 商品推荐助手模式（默认），专注商品推荐，非商品问题引导回商品
    # free: 自由聊天模式，可聊任何话题，工具可用但不强制
    # strict: 严格模式，必须基于工具输出或历史对话回答，否则返回受控失败
    CHAT_MODE: str = "natural"

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
    def effective_embedding_api_key(self) -> str:
        """获取有效的 Embedding API Key"""
        return self.EMBEDDING_API_KEY or self.LLM_API_KEY

    @property
    def effective_embedding_base_url(self) -> str:
        """获取有效的 Embedding Base URL"""
        return self.EMBEDDING_BASE_URL or self.LLM_BASE_URL

    @property
    def effective_rerank_api_key(self) -> str:
        """获取有效的 Rerank API Key"""
        return self.RERANK_API_KEY or self.LLM_API_KEY

    @property
    def effective_rerank_base_url(self) -> str:
        """获取有效的 Rerank Base URL"""
        return self.RERANK_BASE_URL or self.LLM_BASE_URL

    @property
    def effective_rerank_provider(self) -> str:
        """获取有效的 Rerank 提供商"""
        return self.RERANK_PROVIDER or self.LLM_PROVIDER

    @property
    def effective_models_dev_provider_id(self) -> str:
        """获取有效的 models.dev provider ID"""
        return self.MODELS_DEV_PROVIDER_ID or self.LLM_PROVIDER

    @property
    def model_profiles(self) -> dict[str, dict[str, Any]]:
        """解析 .env 中的模型 profile JSON 配置"""
        raw = (self.MODEL_PROFILES_JSON or "").strip()
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
