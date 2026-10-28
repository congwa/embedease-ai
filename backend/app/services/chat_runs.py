"""限制进程内聊天运行数量，防止同一会话同时改写 Agent 状态。"""

from dataclasses import dataclass

from fastapi import HTTPException

from app.core.config import settings


@dataclass
class ChatRunLease:
    """覆盖请求准备、模型运行及流式落库全过程的运行名额。"""

    coordinator: "ChatRunCoordinator"
    conversation_id: str
    released: bool = False

    def release(self) -> None:
        """幂等释放名额，允许生成器和响应后台清理重复调用。"""
        if not self.released:
            self.released = True
            self.coordinator._active.discard(self.conversation_id)


class ChatRunCoordinator:
    """单事件循环内原子准入；不同会话可并行，同一会话只运行一轮。"""

    def __init__(self) -> None:
        """只保存活动会话，完成后清理以避免长期积累会话锁。"""
        self._active: set[str] = set()

    def acquire(self, conversation_id: str) -> ChatRunLease:
        """在写入用户消息前拒绝重复或超额请求，不建立无界等待队列。"""
        if conversation_id in self._active:
            raise HTTPException(status_code=409, detail="当前会话正在回复，请等待完成后再发送")
        if len(self._active) >= settings.CHAT_MAX_CONCURRENT_RUNS:
            raise HTTPException(
                status_code=503,
                detail="智能助手繁忙，请稍后重试",
                headers={"Retry-After": "5"},
            )
        # 无 await，检查和登记在当前事件循环中不会被其他请求穿插。
        self._active.add(conversation_id)
        return ChatRunLease(self, conversation_id)


chat_run_coordinator = ChatRunCoordinator()
