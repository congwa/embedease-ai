# 任务调度器模块

统一的任务调度系统，支持单站点多任务场景。基于 APScheduler 实现，提供 cron 和 interval 两种调度方式。

## 设计架构

### 核心组件

```
scheduler/
├── __init__.py              # 模块入口
├── registry.py              # 任务注册中心
├── scheduler.py             # 调度器核心
├── runner.py                # 任务执行器
├── tasks/
│   ├── base.py              # 任务抽象基类
│   ├── crawl_site.py        # 爬虫任务实现
│   └── ...                  # 其他任务实现
├── state/
│   └── models.py            # 状态模型
└── routers/
    └── tasks.py             # API 路由
```

### 组件职责

| 组件 | 职责 |
|------|------|
| **BaseTask** | 任务抽象基类，定义 `name`、`schedule`、`run()` 接口 |
| **TaskRegistry** | 任务注册中心，管理所有任务实例，支持启用/禁用 |
| **TaskScheduler** | 调度器核心，基于 APScheduler 为每个任务创建定时 job |
| **TaskRunner** | 任务执行器，处理超时、异常捕获、记录执行结果 |
| **TaskState** | 任务运行时状态（下次执行时间、上次结果等） |
| **TaskExecutionRecord** | 任务执行历史记录 |

### 执行流程

```
1. App 启动
   ↓
2. 注册任务到 TaskRegistry
   task_registry.register(CrawlSiteTask())
   ↓
3. 启动 TaskScheduler
   await task_scheduler.start()
   ↓
4. 调度器为每个任务创建 APScheduler job
   ↓
5. 到达执行时间
   ↓
6. TaskRunner 执行任务
   - 检查并发控制
   - 执行 task.run()
   - 记录执行结果
   ↓
7. 更新 TaskState（下次执行时间、执行次数等）
```

## 如何扩展新任务

### 步骤 1：创建任务类

在 `tasks/` 目录下创建新文件，继承 `BaseTask`：

```python
# backend/app/scheduler/tasks/sync_inventory.py
from app.scheduler.tasks.base import (
    BaseTask,
    ScheduleType,
    TaskResult,
    TaskSchedule,
)

class SyncInventoryTask(BaseTask):
    """库存同步任务"""
    
    name = "sync_inventory"
    description = "定时同步商品库存数据"
    
    # 定义调度策略
    schedule = TaskSchedule(
        schedule_type=ScheduleType.INTERVAL,
        interval_seconds=3600,  # 每小时执行一次
        allow_concurrent=False,  # 不允许并发执行
    )
    
    enabled = True  # 默认启用
    
    async def run(self) -> TaskResult:
        """执行任务逻辑
        
        Returns:
            TaskResult: 执行结果
        """
        try:
            # 1. 执行业务逻辑
            # await some_service.sync_inventory()
            
            # 2. 返回成功结果
            return TaskResult.success(
                "库存同步完成",
                synced_count=100,
                failed_count=0,
            )
        except Exception as e:
            # 3. 返回失败结果
            return TaskResult.failed(
                error=str(e),
                message="库存同步失败",
            )
```

### 步骤 2：注册任务

在 `tasks/__init__.py` 中导出新任务：

```python
# backend/app/scheduler/tasks/__init__.py
from app.scheduler.tasks.crawl_site import CrawlSiteTask
from app.scheduler.tasks.sync_inventory import SyncInventoryTask

__all__ = [
    "CrawlSiteTask",
    "SyncInventoryTask",
]
```

### 步骤 3：在应用启动时注册

在 `main.py` 中注册任务：

```python
# backend/app/main.py
from app.scheduler import task_registry, task_scheduler
from app.scheduler.tasks import CrawlSiteTask, SyncInventoryTask

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 注册任务
    task_registry.register(CrawlSiteTask())
    task_registry.register(SyncInventoryTask())
    
    # 启动调度器
    await task_scheduler.start()
    
    yield
    
    # 关闭调度器
    await task_scheduler.stop()
```

完成！任务将自动按照配置的调度策略执行。

## 调度策略配置

### Cron 表达式

```python
schedule = TaskSchedule(
    schedule_type=ScheduleType.CRON,
    cron_expression="0 2 * * *",  # 每天凌晨 2 点
)
```

常用 cron 表达式：
- `"0 * * * *"` - 每小时整点
- `"0 2 * * *"` - 每天凌晨 2 点
- `"0 0 * * 0"` - 每周日凌晨
- `"0 0 1 * *"` - 每月 1 号凌晨

### 固定间隔

```python
schedule = TaskSchedule(
    schedule_type=ScheduleType.INTERVAL,
    interval_seconds=3600,  # 每小时
)
```

### 并发控制

```python
schedule = TaskSchedule(
    schedule_type=ScheduleType.CRON,
    cron_expression="0 * * * *",
    allow_concurrent=False,  # 禁止并发，上次未完成则跳过
)
```

## API 接口

调度器提供了完整的 REST API：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/scheduler/status` | GET | 获取调度器状态和所有任务信息 |
| `/scheduler/tasks` | GET | 列出所有注册的任务 |
| `/scheduler/tasks/{name}` | GET | 获取指定任务的详细状态 |
| `/scheduler/tasks/{name}/trigger` | POST | 手动触发任务执行 |
| `/scheduler/tasks/{name}/enable` | POST | 启用任务 |
| `/scheduler/tasks/{name}/disable` | POST | 禁用任务 |
| `/scheduler/tasks/{name}/history` | GET | 获取任务执行历史 |

### 示例：手动触发任务

```bash
curl -X POST http://localhost:8000/scheduler/tasks/crawl_site/trigger
```

### 示例：查看任务状态

```bash
curl http://localhost:8000/scheduler/status
```

响应：
```json
{
  "running": true,
  "task_count": 2,
  "tasks": [
    {
      "name": "crawl_site",
      "description": "定时爬取站点内容",
      "enabled": true,
      "schedule_type": "cron",
      "cron_expression": "0 2 * * *",
      "status": "idle",
      "next_run_at": "2025-12-26T02:00:00",
      "last_run_at": "2025-12-25T02:00:00",
      "last_result": "success",
      "run_count": 10,
      "fail_count": 0
    }
  ]
}
```

## 任务结果类型

### 成功

```python
return TaskResult.success(
    "操作成功",
    processed_count=100,
    duration_seconds=5.2,
)
```

### 失败

```python
return TaskResult.failed(
    error="数据库连接失败",
    message="同步失败",
)
```

### 跳过

```python
return TaskResult.skipped("没有需要处理的数据")
```

## 最佳实践

### 1. 任务命名规范

- 使用小写字母和下划线：`sync_inventory`、`crawl_site`
- 名称应清晰描述任务功能

### 2. 错误处理

```python
async def run(self) -> TaskResult:
    try:
        # 业务逻辑
        result = await self._do_work()
        return TaskResult.success("完成", **result)
    except SpecificError as e:
        logger.error("任务失败", error=str(e))
        return TaskResult.failed(str(e))
    except Exception as e:
        logger.exception("未知错误")
        return TaskResult.failed(f"未知错误: {str(e)}")
```

### 3. 日志记录

```python
from app.core.logging import get_logger

logger = get_logger("scheduler.tasks.my_task")

async def run(self) -> TaskResult:
    logger.info("开始执行任务", param1=value1)
    # ...
    logger.info("任务完成", result_count=count)
```

### 4. 超时控制

任务执行器默认超时时间为 3600 秒（1 小时）。如需自定义：

```python
# 在 TaskRunner 初始化时设置
runner = TaskRunner(default_timeout=1800)  # 30 分钟
```

### 5. 依赖注入

如果任务需要访问数据库或其他服务：

```python
from app.core.database import get_db_context

async def run(self) -> TaskResult:
    async with get_db_context() as session:
        # 使用 session 进行数据库操作
        repo = MyRepository(session)
        data = await repo.get_all()
        # ...
```

## 监控与调试

### 查看执行历史

```python
# 获取最近 10 次执行记录
records = task_scheduler.runner.get_history("crawl_site", limit=10)

for record in records:
    print(f"{record.started_at}: {record.status} - {record.message}")
```

### 查看任务状态

```python
state = task_scheduler.runner.get_state("crawl_site")
print(f"下次执行: {state.next_run_at}")
print(f"执行次数: {state.run_count}")
print(f"失败次数: {state.fail_count}")
```

### 动态启用/禁用

```python
# 禁用任务
task_registry.disable("crawl_site")

# 启用任务
task_registry.enable("crawl_site")
```

## 注意事项

1. **单站点场景**：当前架构针对单站点设计，所有任务共享同一个调度器实例。
2. **状态持久化**：任务状态目前存储在内存中，重启后会丢失。如需持久化可扩展 `TaskRunner`。
3. **并发限制**：通过 `allow_concurrent=False` 防止同一任务重叠执行。
4. **异常处理**：任务执行器会自动捕获所有异常，不会导致调度器崩溃。
5. **日志集中**：所有日志通过 `loggerService` 统一管理，便于追踪。

## 未来扩展方向

如果需要支持更多站点或分布式调度，可考虑：

1. **持久化 JobStore**：使用 Redis 或数据库存储任务状态
2. **分布式锁**：防止多实例重复执行
3. **任务队列**：将调度与执行解耦（如 Celery、RQ）
4. **动态配置**：从数据库读取任务配置，支持运行时修改
