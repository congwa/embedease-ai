"""Domain event emitter：供工具/中间件在任意位置发出事件。

这是"内部事件（domain event）"层：
- 输入：`type: str` + `payload: Any`
- 输出：推入 orchestrator 管理的队列（由 orchestrator 统一封装为 `StreamEvent` 并 SSE 推送）

注意：工具可能在不同线程执行，因此这里使用 `loop.call_soon_threadsafe` 保证线程安全。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class QueueDomainEmitter:
    """将 domain event 推入 asyncio.Queue（线程安全）。"""

    queue: "asyncio.Queue[dict[str, Any]]"
    loop: asyncio.AbstractEventLoop

    def emit(self, type: str, payload: Any) -> None:
        """同步发射（线程安全）
        
        工具可能在不同线程里执行（取决于 tool runner），用 call_soon_threadsafe 更稳。
        """
        evt: dict[str, Any] = {"type": type, "payload": payload}

        def _put() -> None:
            try:
                self.queue.put_nowait(evt)
            except asyncio.QueueFull:
                try:
                    self.loop.create_task(self.queue.put(evt))
                except RuntimeError:
                    return

        self.loop.call_soon_threadsafe(_put)

    async def aemit(self, type: str, payload: Any) -> None:
        """异步发射（严格顺序）
        
        适用于高频/不允许丢失的事件（例如逐字推理 assistant.reasoning.delta）。
        """
        evt: dict[str, Any] = {"type": type, "payload": payload}
        await self.queue.put(evt)
