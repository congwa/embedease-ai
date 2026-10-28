"""每实例串行执行文档任务，数据库租约负责跨实例互斥和重启恢复。"""

import time

from app.core.config import settings
from app.core.logging import get_logger
from app.scheduler.tasks.base import BaseTask, ScheduleType, TaskResult, TaskSchedule
from app.services.knowledge.rag.worker import run_once, sweep_orphans

logger = get_logger("knowledge.scheduler")


class KnowledgeIngestionTask(BaseTask):
    """复用现有调度生命周期，不创建只存在内存中的入库队列。"""

    name = "knowledge_ingestion_task"
    description = "处理托管知识库入库和清理任务"
    schedule = TaskSchedule(
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=5,
        allow_concurrent=False,
        run_on_start=True,
    )

    def __init__(self):
        """每小时执行一次孤儿对象及删除墓碑对账。"""
        self._last_sweep = 0.0

    async def run(self) -> TaskResult:
        """单次仅处理一个任务，避免批量导入占满进程。"""
        if not settings.KNOWLEDGE_WORKER_ENABLED or not settings.KNOWLEDGE_RAG_ENABLED:
            return TaskResult.skipped("知识库任务执行器已停用")
        processed = await run_once()
        if (
            settings.MINIO_ENABLED
            and settings.KNOWLEDGE_ADMIN_KEY
            and time.time() - self._last_sweep > 3600
        ):
            self._last_sweep = time.time()
            try:
                await sweep_orphans()
            except Exception as exc:
                logger.warning("知识库清理巡检失败", error=type(exc).__name__)
        return TaskResult.success(processed=processed)
