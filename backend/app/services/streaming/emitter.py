"""Domain event emitter：供工具/中间件在任意位置发出事件。

这是“内部事件（domain event）”层：
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
        evt: dict[str, Any] = {"type": type, "payload": payload}

        # 工具可能在不同线程里执行（取决于 tool runner），用 call_soon_threadsafe 更稳
        def _put() -> None:
            try:
                self.queue.put_nowait(evt)
            except asyncio.QueueFull:
                # 极端情况下丢弃事件，避免阻塞业务执行
                pass

        self.loop.call_soon_threadsafe(_put)
