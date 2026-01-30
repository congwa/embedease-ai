"""聊天集成测试配置

配置独立的测试数据库，避免 SQLite 并发锁问题
"""

import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# 创建测试专用目录
_test_data_dir = Path(tempfile.mkdtemp(prefix="chat_test_"))
_db_initialized = False

# 日志目录
_logs_dir = Path(__file__).parent / "logs"
_logs_dir.mkdir(exist_ok=True)


def pytest_configure(config):
    """pytest 配置钩子 - 在任何测试导入之前设置环境变量"""
    # 先加载 .env 文件，覆盖 tests/conftest.py 中的默认值
    from pathlib import Path
    from dotenv import load_dotenv
    _env_path = Path(__file__).parents[3] / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=True)

    os.environ["DATABASE_PATH"] = str(_test_data_dir / "test_app.db")
    os.environ["CHECKPOINT_DB_PATH"] = str(_test_data_dir / "test_checkpoints.db")
    os.environ["CRAWLER_DATABASE_PATH"] = str(_test_data_dir / "test_crawler.db")
    
    # 配置日志输出到文件
    import logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = _logs_dir / f"test_run_{timestamp}.log"
    
    # 配置文件日志处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    ))
    
    # 添加到根日志
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.DEBUG)
    
    # 保存日志文件路径供后续使用
    config._log_file = log_file
    print(f"\n📝 测试日志将写入: {log_file}")

    # 重置数据库 provider 单例
    try:
        import app.core.db.provider as provider_module
        provider_module._provider = None
    except ImportError:
        pass

    # 重置 settings 缓存
    try:
        from app.core.config import get_settings
        get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass

    # 重置 LLM 相关的 lru_cache（避免使用错误的 base_url）
    try:
        from app.core.llm import get_chat_model, get_memory_model, get_embeddings
        get_chat_model.cache_clear()
        get_memory_model.cache_clear()
        get_embeddings.cache_clear()
    except (ImportError, AttributeError):
        pass


def pytest_unconfigure(config):
    """pytest 清理钩子"""
    try:
        shutil.rmtree(_test_data_dir)
    except Exception:
        pass


@pytest.fixture(autouse=True)
async def ensure_db_initialized():
    """确保测试数据库已初始化（每个测试前检查）
    
    重要：每个测试前都要重置 checkpointer，因为 asyncio.Lock 绑定到特定的事件循环。
    pytest-anyio 可能为每个测试创建新的事件循环，导致 Lock 失效。
    """
    global _db_initialized
    
    from app.services.agent.core.service import agent_service

    # 每次测试前都重置 checkpointer（避免事件循环绑定问题）
    agent_service._checkpointer = None
    agent_service._agents = {}  # 清除缓存的 agent 实例
    
    # 重置 checkpointer 单例（完全重置，避免事件循环绑定问题）
    try:
        import app.core.db.checkpointer as checkpointer_module
        # 重置模块级单例
        checkpointer_module._manager = None
        # 重置类级单例
        checkpointer_module.CheckpointerManager._instance = None
    except Exception:
        pass

    if not _db_initialized:
        from app.core.database import init_db

        # 重置 agent_service 其他状态
        agent_service._default_agent_id = None
        agent_service._agent_configs = {}

        # 初始化数据库
        await init_db()

        # 预先初始化 agent_service，创建默认 agent
        try:
            await asyncio.wait_for(
                agent_service.get_default_agent_id(),
                timeout=30
            )
            # 预加载 agent 配置
            await asyncio.wait_for(
                agent_service.get_agent_config(),
                timeout=30
            )
        except asyncio.TimeoutError:
            print("Warning: agent_service initialization timed out")
        except Exception as e:
            print(f"Warning: Failed to pre-initialize agent_service: {e}")

        _db_initialized = True

    yield
