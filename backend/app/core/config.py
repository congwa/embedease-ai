"""应用配置管理"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import get_project_root


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

    # ========== ENV_JSON 目录配置 ==========
    # 支持将复杂 JSON 配置放在独立文件中，提升可读性和可维护性
    # 目录内文件命名规则：<ENV_VAR_NAME>.json（如 MODEL_PROFILES_JSON.json）
    # 加载优先级：.env 中的环境变量 > .env.json 目录中的文件
    # 留空则不启用目录加载，仅使用 .env 中的内联 JSON
    ENV_JSON_DIR: str = ""  # 示例：.env.json

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
    CRAWLER_DATABASE_PATH: str = "./data/crawler.db"  # 爬虫独立数据库

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

    # ========== 商品库画像配置 ==========
    # 导入商品时生成画像摘要，注入 Agent system prompt 指导检索方向
    CATALOG_PROFILE_ENABLED: bool = True  # 是否启用画像注入
    CATALOG_PROFILE_TTL_SECONDS: float = 600.0  # Agent 侧缓存 TTL（秒）
    CATALOG_PROFILE_TOP_CATEGORIES: int = 3  # 画像中展示的 Top 类目数量（建议 3，保证短）

    # ========== Agent 工具执行配置 ==========
    # 工具串行执行：当模型一次返回多个 tool_calls 时，是否强制按顺序执行（而非并行）
    AGENT_SERIALIZE_TOOLS: bool = True

    # ========== Agent TODO 规划中间件配置 ==========
    # 启用后，Agent 会自动注入 write_todos 工具和规划提示，用于复杂多步任务的规划与跟踪
    AGENT_TODO_ENABLED: bool = True  # 是否启用 TodoListMiddleware
    AGENT_TODO_SYSTEM_PROMPT: str | None = None  # 自定义系统提示（可选，留空使用默认）
    AGENT_TODO_TOOL_DESCRIPTION: str | None = None  # 自定义工具描述（可选，留空使用默认）

    # ========== Agent 工具调用限制中间件配置 ==========
    # 限制工具调用次数，防止 Agent 陷入无限循环
    AGENT_TOOL_LIMIT_ENABLED: bool = True  # 是否启用 ToolCallLimitMiddleware
    AGENT_TOOL_LIMIT_THREAD: int | None = None  # 线程级限制（跨 run 累计），留空不限制
    AGENT_TOOL_LIMIT_RUN: int | None = 20  # 单次 run 限制，默认 20
    AGENT_TOOL_LIMIT_EXIT_BEHAVIOR: str = "continue"  # 超限行为: continue/error/end

    # ========== Agent 工具重试中间件配置 ==========
    # 工具调用失败时自动重试
    AGENT_TOOL_RETRY_ENABLED: bool = True  # 是否启用 ToolRetryMiddleware
    AGENT_TOOL_RETRY_MAX_RETRIES: int = 2  # 最大重试次数
    AGENT_TOOL_RETRY_BACKOFF_FACTOR: float = 2.0  # 指数退避因子
    AGENT_TOOL_RETRY_INITIAL_DELAY: float = 1.0  # 初始延迟（秒）
    AGENT_TOOL_RETRY_MAX_DELAY: float = 60.0  # 最大延迟（秒）

    # ========== Agent 上下文压缩中间件配置 ==========
    # 当消息历史过长时自动压缩（使用 LLM 生成摘要替换旧消息）
    AGENT_SUMMARIZATION_ENABLED: bool = True  # 是否启用 SummarizationMiddleware
    # 触发压缩的阈值（消息数），达到此数量时触发压缩
    AGENT_SUMMARIZATION_TRIGGER_MESSAGES: int = 50
    # 压缩后保留的最近消息数
    AGENT_SUMMARIZATION_KEEP_MESSAGES: int = 20
    # 用于生成摘要的最大 token 数（避免摘要请求过大）
    AGENT_SUMMARIZATION_TRIM_TOKENS: int = 4000

    # ========== 记忆系统配置 ==========
    # 总开关
    MEMORY_ENABLED: bool = True

    # LangGraph Store（长期记忆基座）
    MEMORY_STORE_ENABLED: bool = True
    MEMORY_STORE_DB_PATH: str = "./data/memory_store.db"

    # Memory 专用模型配置（可以与聊天模型不同，例如使用更便宜的模型）
    MEMORY_MODEL: str | None = None  # Memory 专用模型，留空则使用 LLM_CHAT_MODEL
    MEMORY_PROVIDER: str | None = None  # Memory 提供商，留空则使用 LLM_PROVIDER
    MEMORY_API_KEY: str | None = None  # Memory API Key，留空则使用 LLM_API_KEY
    MEMORY_BASE_URL: str | None = None  # Memory Base URL，留空则使用 LLM_BASE_URL

    # 事实型长期记忆（Qdrant 向量检索）
    MEMORY_FACT_ENABLED: bool = True
    MEMORY_FACT_DB_PATH: str = "./data/facts.db"
    MEMORY_FACT_COLLECTION: str = "memory_facts"  # Qdrant 独立集合
    MEMORY_FACT_SIMILARITY_THRESHOLD: float = 0.5  # Qdrant 距离阈值（越小越相似）
    MEMORY_FACT_MAX_RESULTS: int = 10

    # 图谱记忆
    MEMORY_GRAPH_ENABLED: bool = True
    MEMORY_GRAPH_FILE_PATH: str = "./data/knowledge_graph.jsonl"

    # 记忆编排
    MEMORY_ORCHESTRATION_ENABLED: bool = True
    MEMORY_ASYNC_WRITE: bool = True

    # ========== 爬取模块配置 ==========
    # 总开关
    CRAWLER_ENABLED: bool = False  # 是否启用爬取模块

    # 爬取专用模型配置（可以与聊天模型不同，例如使用更便宜的模型）
    CRAWLER_MODEL: str | None = None  # 爬取专用模型，留空则使用 LLM_CHAT_MODEL
    CRAWLER_PROVIDER: str | None = None  # 爬取提供商，留空则使用 LLM_PROVIDER
    CRAWLER_API_KEY: str | None = None  # 爬取 API Key，留空则使用 LLM_API_KEY
    CRAWLER_BASE_URL: str | None = None  # 爬取 Base URL，留空则使用 LLM_BASE_URL

    # 浏览器配置
    CRAWLER_HEADLESS: bool = True  # 是否无头模式
    CRAWLER_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # 爬取限制
    CRAWLER_MAX_HTML_LENGTH: int = 50000  # LLM 解析的最大 HTML 长度
    CRAWLER_DEFAULT_DELAY: float = 1.0  # 默认请求间隔（秒）
    CRAWLER_DEFAULT_MAX_DEPTH: int = 3  # 默认最大爬取深度
    CRAWLER_DEFAULT_MAX_PAGES: int = 500  # 默认最大页面数

    # 调度配置
    CRAWLER_SCHEDULE_CHECK_INTERVAL: int = 5  # 调度检查间隔（分钟）
    CRAWLER_RUN_ON_START: bool = False  # 调度器启动时是否立即执行一次

    # 站点配置（JSON 数组格式）
    # 结构：JSON 数组，每个元素是 site_initializer 导入的站点定义，常用字段：
    #   id（可缺省自动生成）、name、start_url、status、link_pattern、
    #   max_depth、max_pages、crawl_delay、is_spa、wait_for_selector、
    #   wait_timeout、extraction_config、cron_expression。
    # 运行机制：应用启动时解析此字段 -> 批量创建/更新站点 -> 按 cron 注册任务。
    CRAWLER_SITES_JSON: str = ""  # 示例：[{"id":"site_id","name":"站点名","start_url":"https://...","cron_expression":"0 2 * * *",...}]

    # ========== 客服支持配置 ==========
    # 企业微信通知配置
    WEWORK_CORP_ID: str = ""  # 企业 ID
    WEWORK_AGENT_ID: str = ""  # 应用 ID
    WEWORK_AGENT_SECRET: str = ""  # 应用 Secret
    WEWORK_NOTIFY_USERS: str = "@all"  # 接收通知的用户（逗号分隔或 @all）

    # 通用 Webhook 通知配置
    NOTIFY_WEBHOOK_URL: str = ""  # Webhook URL
    NOTIFY_WEBHOOK_SECRET: str = ""  # 可选的签名密钥

    # 客服控制台配置
    SUPPORT_CONSOLE_URL: str = ""  # 客服控制台 URL（用于通知中的链接）
    SUPPORT_SLA_SECONDS: int = 120  # SLA 等待时间（秒），超过后发送提醒

    @property
    def crawler_sites(self) -> list[dict[str, Any]]:
        """
        解析爬虫站点配置
        
        支持两种加载方式：
        1. 从 .env 的 CRAWLER_SITES_JSON 环境变量加载（单行 JSON）
        2. 从 ENV_JSON_DIR/CRAWLER_SITES_JSON.json 文件加载（多行格式化 JSON）
        
        优先级：环境变量 > 文件
        """
        parsed = self._load_json_from_env_or_file("CRAWLER_SITES_JSON", self.CRAWLER_SITES_JSON)
        if parsed is None:
            return []
        if not isinstance(parsed, list):
            return []
        return parsed

    @property
    def database_url(self) -> str:
        """SQLite 数据库 URL"""
        return f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    @property
    def crawler_database_url(self) -> str:
        """爬虫 SQLite 数据库 URL"""
        return f"sqlite+aiosqlite:///{self.CRAWLER_DATABASE_PATH}"

    @property
    def cors_origins_list(self) -> list[str]:
        """
        CORS 允许的源列表
        
        支持三种加载方式：
        1. 从 .env 的 CORS_ORIGINS 环境变量加载（逗号分隔字符串）
        2. 从 ENV_JSON_DIR/CORS_ORIGINS.json 文件加载（JSON 数组）
        
        优先级：环境变量 > 文件
        """
        # 尝试从 JSON 加载
        parsed = self._load_json_from_env_or_file("CORS_ORIGINS", self.CORS_ORIGINS)
        if parsed is not None:
            if isinstance(parsed, list):
                return [str(origin).strip() for origin in parsed]
            # 如果是字符串，按逗号分隔
            if isinstance(parsed, str):
                return [origin.strip() for origin in parsed.split(",")]
        
        # 回退到默认的逗号分隔处理
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def ensure_data_dir(self) -> None:
        """确保数据目录存在"""
        Path(self.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.CHECKPOINT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.CRAWLER_DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

    def ensure_memory_dirs(self) -> None:
        """确保记忆相关目录存在"""
        Path(self.MEMORY_STORE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.MEMORY_FACT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(self.MEMORY_GRAPH_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

    def _load_json_from_env_or_file(self, var_name: str, env_value: str) -> Any:
        """
        通用 JSON 配置加载函数，支持从环境变量或 .env.json 目录加载
        
        加载优先级：
        1. 优先使用 .env 中的环境变量（env_value）
        2. 若环境变量为空，尝试从 ENV_JSON_DIR/<var_name>.json 加载
        3. 若都不存在，返回 None
        
        Args:
            var_name: 环境变量名（如 "MODEL_PROFILES_JSON"）
            env_value: .env 中的环境变量值
            
        Returns:
            解析后的 JSON 对象（dict/list），失败返回 None
            
        示例：
            # .env 中设置
            ENV_JSON_DIR=.env.json
            
            # .env.json/MODEL_PROFILES_JSON.json 内容
            {
              "model1": {"capability": "value"}
            }
            
            # 调用
            result = self._load_json_from_env_or_file("MODEL_PROFILES_JSON", self.MODEL_PROFILES_JSON)
        """
        # 1. 优先使用环境变量
        raw = (env_value or "").strip()
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # 环境变量解析失败，记录但不中断，继续尝试文件
                pass
        
        # 2. 尝试从 .env.json 目录加载
        if not self.ENV_JSON_DIR:
            return None
            
        env_dir = Path(self.ENV_JSON_DIR)
        if not env_dir.is_absolute():
            project_root = get_project_root()
            env_dir = (project_root / env_dir).resolve()
        json_file = env_dir / f"{var_name}.json"
        if not json_file.exists():
            return None
            
        try:
            content = json_file.read_text(encoding="utf-8")
            # 支持简单的注释剥离（仅支持 // 单行注释）
            def _strip_line_comments(text: str) -> str:
                """移除行尾 // 注释，保留字符串内的内容"""
                cleaned_chars: list[str] = []
                in_string = False
                escape = False
                i = 0
                while i < len(text):
                    ch = text[i]
                    if escape:
                        cleaned_chars.append(ch)
                        escape = False
                        i += 1
                        continue
                    if ch == "\\":
                        cleaned_chars.append(ch)
                        escape = True
                        i += 1
                        continue
                    if ch == '"':
                        in_string = not in_string
                        cleaned_chars.append(ch)
                        i += 1
                        continue
                    if (
                        ch == "/"
                        and not in_string
                        and i + 1 < len(text)
                        and text[i + 1] == "/"
                    ):
                        break
                    cleaned_chars.append(ch)
                    i += 1
                return "".join(cleaned_chars).rstrip()

            cleaned = "\n".join(_strip_line_comments(line) for line in content.split("\n"))
            return json.loads(cleaned)
        except (json.JSONDecodeError, OSError):
            # 文件读取或解析失败
            return None

    @property
    def effective_memory_model(self) -> str:
        """获取有效的 Memory 模型"""
        return self.MEMORY_MODEL or self.LLM_CHAT_MODEL

    @property
    def effective_memory_provider(self) -> str:
        """获取有效的 Memory 提供商"""
        return self.MEMORY_PROVIDER or self.LLM_PROVIDER

    @property
    def effective_memory_api_key(self) -> str:
        """获取有效的 Memory API Key"""
        return self.MEMORY_API_KEY or self.LLM_API_KEY

    @property
    def effective_memory_base_url(self) -> str:
        """获取有效的 Memory Base URL"""
        return self.MEMORY_BASE_URL or self.LLM_BASE_URL

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
        """
        解析模型 profile JSON 配置
        
        支持两种加载方式：
        1. 从 .env 的 MODEL_PROFILES_JSON 环境变量加载（单行 JSON）
        2. 从 ENV_JSON_DIR/MODEL_PROFILES_JSON.json 文件加载（多行格式化 JSON）
        
        优先级：环境变量 > 文件
        """
        parsed = self._load_json_from_env_or_file("MODEL_PROFILES_JSON", self.MODEL_PROFILES_JSON)
        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, dict[str, Any]] = {}
        for k, v in parsed.items():
            if not isinstance(k, str) or not isinstance(v, dict):
                continue
            out[k.strip().lower()] = v
        return out

    @property
    def effective_crawler_model(self) -> str:
        """获取有效的爬取模型"""
        return self.CRAWLER_MODEL or self.LLM_CHAT_MODEL

    @property
    def effective_crawler_provider(self) -> str:
        """获取有效的爬取提供商"""
        return self.CRAWLER_PROVIDER or self.LLM_PROVIDER

    @property
    def effective_crawler_api_key(self) -> str:
        """获取有效的爬取 API Key"""
        return self.CRAWLER_API_KEY or self.LLM_API_KEY

    @property
    def effective_crawler_base_url(self) -> str:
        """获取有效的爬取 Base URL"""
        return self.CRAWLER_BASE_URL or self.LLM_BASE_URL


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
