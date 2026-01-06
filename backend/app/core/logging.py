"""日志系统 - 使用 loguru + structlog + rich

支持配置模式:
- simple: 简洁模式，只显示关键信息
- detailed: 详细模式，显示完整堆栈和上下文
- json: JSON 格式，适合生产环境日志收集

使用方式:
    from app.core.logging import logger

    logger.info("消息")
    logger.debug("调试信息", extra={"user_id": "123"})
    logger.error("错误", exc_info=True)
"""

import asyncio
import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import Any

from loguru import logger as loguru_logger
from rich.console import Console
from rich.traceback import install as install_rich_traceback

from app.core.config import settings
from app.core.paths import get_project_root


class LogLevel(str, Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogMode(str, Enum):
    """日志模式"""

    SIMPLE = "simple"  # 简洁模式
    DETAILED = "detailed"  # 详细模式
    JSON = "json"  # JSON 模式（生产环境）


# Rich 控制台
console = Console(force_terminal=True, color_system="auto")


def _safe_for_logging(value: Any, *, _level: int = 0) -> Any:
    """将任意对象转换为可序列化/可 picklable 的结构，避免 loguru enqueue/serialize 报错。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    # asyncio Future/Task 等不可 picklable
    if isinstance(value, (asyncio.Future, asyncio.Task)):
        return repr(value)

    # 常见容器
    if isinstance(value, dict):
        # 对 tool_calls 字段进行特殊处理，确保 items 列表内容完整显示
        # tool_calls 结构：{"count": int, "items": list, "truncated": bool}
        if "tool_calls" in value and isinstance(value.get("tool_calls"), dict):
            tool_calls = value["tool_calls"]
            if "items" in tool_calls and isinstance(tool_calls["items"], list):
                # 对 items 列表进行特殊处理：保持当前层级，不增加嵌套深度
                # 这样可以确保 items 的内容能够完整显示，即使嵌套层级较深
                items = tool_calls["items"]
                tool_calls["items"] = [
                    _safe_for_logging(item, _level=_level)  # 保持当前层级
                    for item in items
                ]

        if _level >= 8:  # 增加嵌套层级限制从 4 到 8，给 tool_calls.items 更多空间
            return "{...}"
        return {str(k): _safe_for_logging(v, _level=_level + 1) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        if _level >= 8:  # 增加嵌套层级限制从 4 到 8
            return ["..."]
        return [_safe_for_logging(v, _level=_level + 1) for v in value]

    # Path 等
    if isinstance(value, Path):
        return str(value)

    # Pydantic 模型
    if hasattr(value, "model_dump"):
        try:
            # ChatContext 现在是 Pydantic 模型，emitter 字段已通过 Field(exclude=True) 排除
            # 所以直接使用 model_dump() 即可，不需要特殊处理
            return _safe_for_logging(value.model_dump(), _level=_level + 1)
        except Exception:
            return repr(value)

    # 兜底：字符串化（限制长度避免巨日志）
    text = repr(value)
    if len(text) > 2000:
        return text[:2000] + "..."
    return text


def format_simple(record: dict) -> str:
    """简洁格式"""
    level = record["level"].name
    message = record["message"]
    module = record.get("extra", {}).get("module", "app")

    # 颜色映射
    color_map = {
        "DEBUG": "dim",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold red",
    }
    color = color_map.get(level, "white")

    # 转义消息中的特殊字符，避免 colorizer 将其误认为格式指令
    safe_message = (
        message.replace("<", "\\<")
        .replace(">", "\\>")
        .replace("{", "{{")
        .replace("}", "}}")
    )

    return f"<{color}>[{module}]</{color}> {safe_message}\n"


def format_detailed(record: dict) -> str:
    """详细格式"""
    level = record["level"].name
    time = record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    message = record["message"]
    extra = record.get("extra", {})
    module = extra.get("module", "app")

    # 使用相对路径而不是只显示文件名，方便区分同名文件
    file_obj = record.get("file")
    try:
        file_path_str = getattr(file_obj, "path", str(file_obj or ""))
        project_root = get_project_root()
        file = str(Path(file_path_str).resolve().relative_to(project_root))
    except (ValueError, AttributeError, Exception):
        # 如果获取失败，回退到文件名
        file = getattr(file_obj, "name", str(file_obj or ""))

    line = record.get("line", "")
    function = record.get("function", "")

    # 颜色映射
    color_map = {
        "DEBUG": "dim cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold red on white",
    }
    color = color_map.get(level, "white")

    # 基础信息
    header = f"<dim>{time}</dim> <{color}>{level:8}</{color}>"
    location = f"<cyan>{file}:{line}</cyan> in <blue>{function}</blue>"
    module_tag = f"<magenta>[{module}]</magenta>"

    # 额外上下文（转义特殊字符避免被 loguru 解析）
    context_keys = [k for k in extra if k not in ("module",)]
    context = ""
    if context_keys:
        ctx_parts = []
        for k in context_keys:
            # 转义大括号和尖括号，避免被 loguru 解析
            # {} 会被解析为格式化占位符，<> 会被解析为颜色标记
            value_repr = repr(extra[k]).replace("{", "{{").replace("}", "}}").replace("<", "\\<").replace(">", "\\>")
            ctx_parts.append(f"{k}={value_repr}")
        context = f" <dim>| {', '.join(ctx_parts)}</dim>"

    # 转义消息内容中的特殊字符，避免 loguru Colorizer 递归解析
    safe_message = (
        message.replace("<", "\\<")
        .replace(">", "\\>")
        .replace("{", "{{")
        .replace("}", "}}")
    )

    result = f"{header} {module_tag} {location}{context}\n    → {safe_message}\n"

    # 异常信息
    if record.get("exception"):
        exc_type, exc_value, exc_tb = record["exception"]
        if exc_value:
            tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            # loguru 的 formatter 仍会对返回字符串做 format_map，因此必须转义大括号
            tb_str = tb_str.replace("{", "{{").replace("}", "}}")
            result += f"\n<red>{tb_str}</red>\n"

    return result


def format_json(record: dict) -> str:
    """JSON 格式"""
    import json

    extra = record.get("extra", {})

    file_obj = record.get("file")
    # 尝试获取相对路径
    file_path = None
    try:
        file_path_str = getattr(file_obj, "path", None)
        if file_path_str:
            project_root = get_project_root()
            file_path = str(Path(file_path_str).resolve().relative_to(project_root))
    except (ValueError, AttributeError, Exception):
        file_path = getattr(file_obj, "name", None)

    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": extra.get("module", "app"),
        "file": file_path,
        "line": record.get("line", 0),
        "function": record.get("function", ""),
    }

    # 添加额外字段
    for k, v in extra.items():
        if k not in ("module", "file", "line", "function"):
            try:
                json.dumps(v)  # 测试是否可序列化
                log_entry[k] = v
            except (TypeError, ValueError):
                log_entry[k] = str(v)

    # 异常信息
    if record.get("exception"):
        exc_type, exc_value, exc_tb = record["exception"]
        if exc_value:
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value),
                "traceback": traceback.format_exception(exc_type, exc_value, exc_tb),
            }

    return json.dumps(log_entry, ensure_ascii=False, default=str) + "\n"


class Logger:
    """统一日志接口"""

    def __init__(self) -> None:
        self._configured = False
        self._mode = LogMode.DETAILED
        self._level = LogLevel.DEBUG

    def configure(
        self,
        mode: LogMode | str | None = None,
        level: LogLevel | str | None = None,
        log_file: str | None = None,
    ) -> None:
        """配置日志系统

        Args:
            mode: 日志模式 (simple, detailed, json)
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: 日志文件路径，留空则不记录文件
        """
        # 从参数或配置获取设置
        if mode is None:
            mode = getattr(settings, "LOG_MODE", "detailed")
        if level is None:
            level = getattr(settings, "LOG_LEVEL", "DEBUG")
        if log_file is None:
            log_file = getattr(settings, "LOG_FILE", "")

        # 转换为枚举
        if isinstance(mode, str):
            mode = LogMode(mode.lower())
        if isinstance(level, str):
            level = LogLevel(level.upper())

        self._mode = mode
        self._level = level

        # 移除默认处理器
        loguru_logger.remove()

        # 选择格式化器
        if mode == LogMode.SIMPLE:
            formatter = format_simple
        elif mode == LogMode.JSON:
            formatter = format_json
        else:
            formatter = format_detailed
            # 详细模式下安装 Rich traceback
            install_rich_traceback(console=console, show_locals=True, width=120)

        # 添加控制台处理器
        loguru_logger.add(
            sys.stderr,
            format=formatter,
            level=level.value,
            colorize=mode != LogMode.JSON,
            backtrace=mode == LogMode.DETAILED,
            diagnose=mode == LogMode.DETAILED,
            enqueue=True,  # 异步写入，避免阻塞
        )

        # 添加文件处理器
        log_file_configured = False
        if log_file:
            log_path = Path(log_file)
        else:
            # 默认日志文件路径，确保启动阶段的错误也能落盘
            log_path = Path("logs/app.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        rotation = getattr(settings, "LOG_FILE_ROTATION", "10 MB")
        retention = getattr(settings, "LOG_FILE_RETENTION", "7 days")

        # 文件日志使用 JSON 格式（方便解析）
        loguru_logger.add(
            str(log_path),
            format="{message}",
            level=level.value,
            rotation=rotation,
            retention=retention,
            compression="gz",  # 压缩旧日志
            # serialize=True 时 loguru 会通过队列传递 record 对象，要求可 picklable；
            # 这里禁用 enqueue，避免在包含复杂对象时触发 pickling 报错。
            enqueue=False,
            serialize=True,  # 自动序列化为 JSON
        )
        log_file_configured = True

        # 标记为已配置（必须在记录日志之前设置，避免递归）
        self._configured = True

        # 注册全局异常钩子，捕获导入期和运行时异常
        def _global_excepthook(exc_type, exc, tb):
            loguru_logger.bind(module="runtime").opt(exception=(exc_type, exc, tb)).critical(
                "Uncaught exception"
            )

        sys.excepthook = _global_excepthook

        # 尝试为 asyncio 事件循环设置异常处理器
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
        if loop:
            def _asyncio_exception_handler(loop, context):
                msg = context.get("message", "Unhandled asyncio exception")
                exception = context.get("exception")
                if exception:
                    loguru_logger.bind(module="asyncio").opt(exception=(type(exception), exception, exception.__traceback__)).critical(
                        f"Asyncio error: {msg}"
                    )
                else:
                    loguru_logger.bind(module="asyncio").critical(f"Asyncio error: {msg}")

            loop.set_exception_handler(_asyncio_exception_handler)

        # 记录配置完成信息
        if log_file_configured:
            loguru_logger.bind(module="logging").info(
                f"日志文件已配置: {log_file} (rotation={rotation}, retention={retention})"
            )
        loguru_logger.bind(module="logging").info(
            f"日志系统已配置: mode={mode.value}, level={level.value}"
        )

    def _ensure_configured(self) -> None:
        """确保已配置"""
        if not self._configured:
            self.configure()

    def _log(
        self,
        level: str,
        message: str,
        *,
        module: str = "app",
        exc_info: bool = False,
        _depth: int = 0,
        **extra: Any,
    ) -> None:
        """内部日志方法"""
        self._ensure_configured()

        # 合并上下文
        context = {"module": module}
        # 关键：任何 extra 都先转成可序列化/可 picklable，避免 enqueue/serialize 报错
        for k, v in extra.items():
            context[str(k)] = _safe_for_logging(v)

        # 记录日志：使用 loguru 的 opt(depth=...) 获取稳定、准确的 callsite
        # 调用栈（直接调用 Logger）：user -> Logger.info -> _log -> loguru
        # 调用栈（使用 BoundLogger）：user -> BoundLogger.info -> Logger.info -> _log -> loguru
        opt_depth = 2 + _depth
        loguru_logger.bind(**context).opt(depth=opt_depth, exception=exc_info).log(
            level.upper(),
            message,
        )

    def debug(self, message: str, *, module: str = "app", _depth: int = 0, **extra: Any) -> None:
        """调试日志"""
        self._log("debug", message, module=module, _depth=_depth, **extra)

    def info(self, message: str, *, module: str = "app", _depth: int = 0, **extra: Any) -> None:
        """信息日志"""
        self._log("info", message, module=module, _depth=_depth, **extra)

    def warning(self, message: str, *, module: str = "app", _depth: int = 0, **extra: Any) -> None:
        """警告日志"""
        self._log("warning", message, module=module, _depth=_depth, **extra)

    def error(
        self,
        message: str,
        *,
        module: str = "app",
        exc_info: bool = False,
        _depth: int = 0,
        **extra: Any,
    ) -> None:
        """错误日志"""
        self._log("error", message, module=module, exc_info=exc_info, _depth=_depth, **extra)

    def critical(
        self,
        message: str,
        *,
        module: str = "app",
        exc_info: bool = False,
        _depth: int = 0,
        **extra: Any,
    ) -> None:
        """严重错误日志"""
        self._log("critical", message, module=module, exc_info=exc_info, _depth=_depth, **extra)

    def exception(
        self, message: str, *, module: str = "app", _depth: int = 0, **extra: Any
    ) -> None:
        """异常日志（自动包含堆栈）"""
        self._log("error", message, module=module, exc_info=True, _depth=_depth, **extra)

    def bind(self, **context: Any) -> "BoundLogger":
        """创建绑定上下文的日志器"""
        return BoundLogger(self, context)


class BoundLogger:
    """绑定上下文的日志器"""

    def __init__(self, parent: Logger, context: dict[str, Any]) -> None:
        self._parent = parent
        self._context = context

    def debug(self, message: str, **extra: Any) -> None:
        self._parent.debug(message, _depth=1, **{**self._context, **extra})

    def info(self, message: str, **extra: Any) -> None:
        self._parent.info(message, _depth=1, **{**self._context, **extra})

    def warning(self, message: str, **extra: Any) -> None:
        self._parent.warning(message, _depth=1, **{**self._context, **extra})

    def error(self, message: str, exc_info: bool = False, **extra: Any) -> None:
        self._parent.error(message, exc_info=exc_info, _depth=1, **{**self._context, **extra})

    def critical(self, message: str, exc_info: bool = False, **extra: Any) -> None:
        self._parent.critical(message, exc_info=exc_info, _depth=1, **{**self._context, **extra})

    def exception(self, message: str, **extra: Any) -> None:
        self._parent.exception(message, _depth=1, **{**self._context, **extra})


# 全局日志实例
logger = Logger()


# 便捷模块日志创建器
def get_logger(module: str) -> BoundLogger:
    """获取模块专用日志器

    Args:
        module: 模块名称

    Returns:
        绑定了模块名的日志器

    Example:
        from app.core.logging import get_logger

        logger = get_logger("agent")
        logger.info("Agent 初始化")
    """
    return logger.bind(module=module)
