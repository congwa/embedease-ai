"""调度器 API 路由

提供任务调度的查询与控制接口。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.scheduler import task_registry, task_scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# ==================== 响应模型 ====================


class TaskInfo(BaseModel):
    """任务信息"""

    name: str
    description: str
    enabled: bool
    schedule_type: str
    cron_expression: str | None
    interval_seconds: int | None


class TaskStateResponse(BaseModel):
    """任务状态响应"""

    name: str
    description: str
    enabled: bool
    schedule_type: str
    cron_expression: str | None
    interval_seconds: int | None
    status: str
    next_run_at: str | None
    last_run_at: str | None
    last_result: str | None
    run_count: int
    fail_count: int


class SchedulerStatusResponse(BaseModel):
    """调度器状态响应"""

    running: bool
    task_count: int
    tasks: list[TaskStateResponse]


class ExecutionRecordResponse(BaseModel):
    """执行记录响应"""

    id: str
    task_name: str
    started_at: str
    finished_at: str | None
    duration_ms: int | None
    status: str
    message: str
    error: str | None


class TriggerResponse(BaseModel):
    """触发响应"""

    success: bool
    message: str


# ==================== 路由 ====================


@router.get("/status", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """获取调度器状态

    返回调度器运行状态和所有任务的详细信息。
    """
    return task_scheduler.get_status()


@router.get("/tasks", response_model=list[TaskInfo])
async def list_tasks():
    """列出所有注册的任务"""
    tasks = task_registry.list_all()
    return [
        TaskInfo(
            name=t.name,
            description=t.description,
            enabled=t.enabled,
            schedule_type=t.schedule.schedule_type.value,
            cron_expression=t.schedule.cron_expression,
            interval_seconds=t.schedule.interval_seconds,
        )
        for t in tasks
    ]


@router.get("/tasks/{task_name}", response_model=TaskStateResponse)
async def get_task_status(task_name: str):
    """获取任务状态

    Args:
        task_name: 任务名称
    """
    task = task_registry.get(task_name)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_name}",
        )

    state = task_scheduler.runner.get_state(task_name)
    return TaskStateResponse(
        name=task.name,
        description=task.description,
        enabled=task.enabled,
        schedule_type=task.schedule.schedule_type.value,
        cron_expression=task.schedule.cron_expression,
        interval_seconds=task.schedule.interval_seconds,
        status=state.status.value,
        next_run_at=state.next_run_at.isoformat() if state.next_run_at else None,
        last_run_at=state.last_run_at.isoformat() if state.last_run_at else None,
        last_result=state.last_result,
        run_count=state.run_count,
        fail_count=state.fail_count,
    )


@router.post("/tasks/{task_name}/trigger", response_model=TriggerResponse)
async def trigger_task(task_name: str):
    """手动触发任务

    Args:
        task_name: 任务名称
    """
    task = task_registry.get(task_name)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_name}",
        )

    success = await task_scheduler.trigger(task_name)
    if success:
        return TriggerResponse(success=True, message=f"任务 {task_name} 已触发")
    else:
        return TriggerResponse(success=False, message=f"任务 {task_name} 触发失败")


@router.post("/tasks/{task_name}/enable", response_model=TriggerResponse)
async def enable_task(task_name: str):
    """启用任务

    Args:
        task_name: 任务名称
    """
    success = task_registry.enable(task_name)
    if success:
        return TriggerResponse(success=True, message=f"任务 {task_name} 已启用")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_name}",
        )


@router.post("/tasks/{task_name}/disable", response_model=TriggerResponse)
async def disable_task(task_name: str):
    """禁用任务

    Args:
        task_name: 任务名称
    """
    success = task_registry.disable(task_name)
    if success:
        return TriggerResponse(success=True, message=f"任务 {task_name} 已禁用")
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_name}",
        )


@router.get("/tasks/{task_name}/history", response_model=list[ExecutionRecordResponse])
async def get_task_history(task_name: str, limit: int = 10):
    """获取任务执行历史

    Args:
        task_name: 任务名称
        limit: 返回条数（默认10）
    """
    task = task_registry.get(task_name)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_name}",
        )

    records = task_scheduler.runner.get_history(task_name, limit)
    return [
        ExecutionRecordResponse(
            id=r.id,
            task_name=r.task_name,
            started_at=r.started_at.isoformat(),
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
            duration_ms=r.duration_ms,
            status=r.status,
            message=r.message,
            error=r.error,
        )
        for r in records
    ]
