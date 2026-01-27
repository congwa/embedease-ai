"""Quick Setup 状态管理

管理 Quick Setup 向导的状态，包括：
- 步骤进度
- 当前配置的 Agent
- 持久化存储（使用 JSON 文件或数据库）
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.schemas.quick_setup import (
    QuickSetupState,
    QuickSetupStateUpdate,
    SetupStep,
    SetupStepStatus,
)

logger = get_logger("quick_setup.state_manager")


# 基础步骤定义（模式无关）
BASE_STEPS = [
    SetupStep(
        index=0,
        key="welcome",
        title="欢迎 & 检查清单",
        description="查看系统配置状态，了解需要完成的配置项",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=1,
        key="mode",
        title="模式选择",
        description="选择单 Agent 模式或 Supervisor 多 Agent 编排模式",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=2,
        key="system",
        title="系统基础设置",
        description="配置公司信息、品牌主题等基础设置",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=3,
        key="models",
        title="模型 & 向量服务",
        description="配置 LLM、Embedding 和 Qdrant 服务",
        status=SetupStepStatus.PENDING,
    ),
]

# 单 Agent 模式专用步骤
SINGLE_AGENT_STEPS = [
    SetupStep(
        index=4,
        key="agent-type",
        title="Agent 类型选择",
        description="选择要配置的 Agent 类型",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=5,
        key="knowledge",
        title="知识 & Agent 配置",
        description="根据 Agent 类型配置知识源和工具",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=6,
        key="greeting",
        title="开场白配置",
        description="设置 Agent 的欢迎消息和触发策略",
        status=SetupStepStatus.PENDING,
    ),
]

# Supervisor 模式专用步骤
SUPERVISOR_STEPS = [
    SetupStep(
        index=4,
        key="supervisor",
        title="多 Agent 编排",
        description="配置子 Agent 和路由策略",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=5,
        key="greeting",
        title="开场白配置",
        description="设置调度器的欢迎消息",
        status=SetupStepStatus.PENDING,
    ),
]

# 通用结束步骤
END_STEPS = [
    SetupStep(
        index=0,  # index 会在 build_steps 中重新计算
        key="channel",
        title="渠道 & 集成",
        description="配置客服入口和第三方集成",
        status=SetupStepStatus.PENDING,
    ),
    SetupStep(
        index=0,
        key="summary",
        title="总结 & 快捷入口",
        description="查看配置完成状态，获取常用入口",
        status=SetupStepStatus.PENDING,
    ),
]


def build_steps(mode: str = "single") -> list[SetupStep]:
    """根据模式构建步骤列表"""
    if mode == "supervisor":
        middle_steps = SUPERVISOR_STEPS
    else:
        middle_steps = SINGLE_AGENT_STEPS
    
    all_steps = []
    for step in BASE_STEPS:
        all_steps.append(step.model_copy())
    for step in middle_steps:
        all_steps.append(step.model_copy())
    for step in END_STEPS:
        all_steps.append(step.model_copy())
    
    # 重新计算 index
    for i, step in enumerate(all_steps):
        step.index = i
    
    return all_steps


# 默认步骤（单 Agent 模式）
DEFAULT_STEPS = build_steps("single")


class QuickSetupStateManager:
    """Quick Setup 状态管理器
    
    使用 JSON 文件持久化状态，支持多用户场景可扩展为数据库存储。
    """

    def __init__(self, storage_path: str = "./data/quick_setup_state.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._state: QuickSetupState | None = None

    def _load_state(self) -> QuickSetupState:
        """从文件加载状态"""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                # 转换 steps 中的 status 枚举
                if "steps" in data:
                    for step in data["steps"]:
                        if isinstance(step.get("status"), str):
                            step["status"] = SetupStepStatus(step["status"])
                return QuickSetupState.model_validate(data)
            except Exception as e:
                logger.warning("加载 Quick Setup 状态失败，使用默认状态", error=str(e))
        
        # 返回默认状态
        return QuickSetupState(
            completed=False,
            current_step=0,
            steps=[step.model_copy() for step in DEFAULT_STEPS],
            agent_id=None,
            updated_at=datetime.now(),
        )

    def _save_state(self, state: QuickSetupState) -> None:
        """保存状态到文件"""
        state.updated_at = datetime.now()
        data = state.model_dump(mode="json")
        self.storage_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._state = state

    def get_state(self) -> QuickSetupState:
        """获取当前状态"""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def update_state(self, update: QuickSetupStateUpdate) -> QuickSetupState:
        """更新状态"""
        state = self.get_state()
        
        if update.completed is not None:
            state.completed = update.completed
        if update.current_step is not None:
            state.current_step = update.current_step
        if update.steps is not None:
            state.steps = update.steps
        if update.agent_id is not None:
            state.agent_id = update.agent_id
        
        self._save_state(state)
        return state

    def update_step(
        self,
        step_index: int,
        status: SetupStepStatus | None = None,
        data: dict[str, Any] | None = None,
    ) -> QuickSetupState:
        """更新单个步骤"""
        state = self.get_state()
        
        if 0 <= step_index < len(state.steps):
            if status is not None:
                state.steps[step_index].status = status
            if data is not None:
                state.steps[step_index].data = data
        
        self._save_state(state)
        return state

    def complete_step(self, step_index: int, data: dict[str, Any] | None = None) -> QuickSetupState:
        """完成一个步骤并移动到下一步"""
        state = self.get_state()
        
        if 0 <= step_index < len(state.steps):
            state.steps[step_index].status = SetupStepStatus.COMPLETED
            if data is not None:
                state.steps[step_index].data = data
            
            # 移动到下一步
            if step_index + 1 < len(state.steps):
                state.current_step = step_index + 1
                state.steps[step_index + 1].status = SetupStepStatus.IN_PROGRESS
            else:
                # 所有步骤完成
                state.completed = True
        
        self._save_state(state)
        return state

    def skip_step(self, step_index: int) -> QuickSetupState:
        """跳过一个步骤"""
        state = self.get_state()
        
        if 0 <= step_index < len(state.steps):
            state.steps[step_index].status = SetupStepStatus.SKIPPED
            
            # 移动到下一步
            if step_index + 1 < len(state.steps):
                state.current_step = step_index + 1
                state.steps[step_index + 1].status = SetupStepStatus.IN_PROGRESS
        
        self._save_state(state)
        return state

    def go_to_step(self, step_index: int) -> QuickSetupState:
        """跳转到指定步骤"""
        state = self.get_state()
        
        if 0 <= step_index < len(state.steps):
            state.current_step = step_index
            state.steps[step_index].status = SetupStepStatus.IN_PROGRESS
        
        self._save_state(state)
        return state

    def reset(self) -> QuickSetupState:
        """重置状态"""
        state = QuickSetupState(
            completed=False,
            current_step=0,
            steps=[step.model_copy() for step in DEFAULT_STEPS],
            agent_id=None,
            updated_at=datetime.now(),
        )
        state.steps[0].status = SetupStepStatus.IN_PROGRESS
        self._save_state(state)
        return state

    def set_agent(self, agent_id: str) -> QuickSetupState:
        """设置当前配置的 Agent"""
        state = self.get_state()
        state.agent_id = agent_id
        self._save_state(state)
        return state

    def set_mode(self, mode: str) -> QuickSetupState:
        """设置向导模式，动态调整后续步骤
        
        Args:
            mode: "single" | "supervisor"
        """
        state = self.get_state()
        
        # 保存 mode 选择步骤的已完成状态
        mode_step_index = 1  # mode 步骤的 index
        
        # 构建新的步骤列表
        new_steps = build_steps(mode)
        
        # 保留已完成步骤的状态（前 4 个基础步骤）
        for i in range(min(len(state.steps), len(BASE_STEPS))):
            if state.steps[i].status == SetupStepStatus.COMPLETED:
                new_steps[i].status = SetupStepStatus.COMPLETED
                new_steps[i].data = state.steps[i].data
        
        # 设置 mode 步骤为已完成
        new_steps[mode_step_index].status = SetupStepStatus.COMPLETED
        new_steps[mode_step_index].data = {"mode": mode}
        
        # 更新状态
        state.steps = new_steps
        state.current_step = mode_step_index + 1  # 移动到下一步
        new_steps[state.current_step].status = SetupStepStatus.IN_PROGRESS
        
        self._save_state(state)
        logger.info("设置向导模式", mode=mode, total_steps=len(new_steps))
        return state

    def get_current_mode(self) -> str | None:
        """获取当前模式"""
        state = self.get_state()
        mode_step = next((s for s in state.steps if s.key == "mode"), None)
        if mode_step and mode_step.data:
            return mode_step.data.get("mode")
        return None


# 全局实例
_state_manager: QuickSetupStateManager | None = None


def get_state_manager() -> QuickSetupStateManager:
    """获取状态管理器单例"""
    global _state_manager
    if _state_manager is None:
        _state_manager = QuickSetupStateManager()
    return _state_manager
