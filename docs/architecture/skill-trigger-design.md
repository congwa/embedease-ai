# Skill 触发机制设计文档（方案 C：混合模式）

基于现有 SSE 事件流架构，设计 Skill 触发的完整消息流和前端渲染方案。

## 1. 设计原则

| 原则 | 说明 |
|-----|-----|
| **最小干扰** | 技能激活不应打断对话流 |
| **透明可见** | 用户应能知道哪些技能在生效 |
| **渐进增强** | 复用现有架构，最小改动 |
| **性能优先** | always_apply 技能静默注入，无网络开销 |

---

## 2. 技能触发分类

### 2.1 三种触发方式

| 触发方式 | 时机 | 后端行为 | 前端展示 |
|---------|-----|---------|---------|
| **静默注入** | Agent 初始化时 | 将 `always_apply=true` 技能内容注入 system prompt | 无 |
| **关键词触发** | 用户消息匹配关键词 | 发送 `skill.activated` 事件 | 轻提示 Badge |
| **AI 主动调用** | AI 决定加载技能 | 使用 `load_skill` 工具 | 工具卡片（可选隐藏） |

### 2.2 触发流程图

```
用户发送消息
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                    Agent 处理流程                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. System Prompt 已包含 always_apply 技能 (静默)       │
│     └─ 无事件发送                                       │
│                                                         │
│  2. 消息预处理：关键词匹配                              │
│     └─ 匹配成功 → 发送 skill.activated 事件            │
│     └─ 注入技能内容到当前轮次上下文                     │
│                                                         │
│  3. LLM 调用                                            │
│     └─ AI 可能调用 load_skill 工具                      │
│     └─ 发送 tool.start / tool.end 事件                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
     │
     ▼
前端渲染响应
```

---

## 3. 后端实现设计

### 3.1 新增事件类型

```python
# backend/app/schemas/events.py

class StreamEventType(str, Enum):
    # ... 现有事件 ...
    
    # 新增：技能事件
    SKILL_ACTIVATED = "skill.activated"      # 技能被激活（关键词触发）
    SKILL_LOADED = "skill.loaded"            # 技能被加载（AI 主动调用）
```

### 3.2 技能激活 Payload

```python
# backend/app/schemas/stream.py

class SkillActivatedPayload(BaseModel):
    """技能激活事件 Payload"""
    skill_id: str
    skill_name: str
    trigger_type: Literal["keyword", "intent", "manual"]  # 触发方式
    trigger_keyword: str | None = None                     # 触发的关键词（如有）
    
class SkillLoadedPayload(BaseModel):
    """技能加载事件 Payload（AI 主动调用）"""
    skill_id: str
    skill_name: str
    skill_category: str
```

### 3.3 技能注入服务

```python
# backend/app/services/skill/injector.py

class SkillInjector:
    """技能注入器 - 在 Agent 构建和消息处理时注入技能"""
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
    
    def inject_always_apply_skills(
        self,
        system_prompt: str,
        agent_type: str,
        mode: str,
    ) -> str:
        """注入 always_apply 技能到 system prompt（静默）"""
        skills = self.registry.get_always_apply_skills(agent_type, mode)
        if not skills:
            return system_prompt
        
        skill_context = self.registry.build_skill_context(skills)
        return f"{system_prompt}\n\n{skill_context}"
    
    async def match_and_activate_skills(
        self,
        message: str,
        agent_type: str,
        mode: str,
        emitter: DomainEmitter,
    ) -> list[Skill]:
        """匹配关键词并激活技能，发送事件"""
        matched = self.registry.match_skills(agent_type, mode, message)
        
        # 过滤掉 always_apply（已静默注入）
        triggered = [s for s in matched if not s.always_apply]
        
        for skill in triggered:
            # 发送 skill.activated 事件
            await emitter.emit(
                "skill.activated",
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "trigger_type": "keyword",
                    "trigger_keyword": self._find_matched_keyword(message, skill),
                }
            )
        
        return triggered
    
    def _find_matched_keyword(self, message: str, skill: Skill) -> str | None:
        """找到匹配的关键词"""
        message_lower = message.lower()
        for kw in skill.trigger_keywords:
            if kw.lower() in message_lower:
                return kw
        return None
```

### 3.4 修改 Agent 工厂

```python
# backend/app/services/agent/core/factory.py (修改)

from app.services.skill.injector import SkillInjector
from app.services.skill.registry import skill_registry

async def _build_single_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
    use_structured_output: bool = False,
) -> CompiledStateGraph:
    """构建单个 Agent 实例"""
    
    # 1. 获取 LLM
    model = get_chat_model()
    
    # 2. 构建完整 system prompt
    system_prompt = config.system_prompt
    
    # 2.1 注入 always_apply 技能（静默，无事件）
    injector = SkillInjector(skill_registry)
    system_prompt = injector.inject_always_apply_skills(
        system_prompt,
        agent_type=config.type,
        mode=config.mode,
    )
    
    # 2.2 添加模式后缀
    mode_suffix = MODE_PROMPT_SUFFIX.get(config.mode, "")
    if mode_suffix:
        system_prompt = system_prompt + mode_suffix
    
    # 3. 获取工具列表
    tools = get_tools_for_agent(config)
    
    # 3.1 添加 load_skill 工具（可选）
    if config.enable_skill_tool:
        load_skill_tool = create_load_skill_tool(config, skill_registry)
        tools.append(load_skill_tool)
    
    # ... 后续构建逻辑 ...
```

### 3.5 修改 ChatStreamOrchestrator

```python
# backend/app/services/chat_stream.py (修改)

class ChatStreamOrchestrator:
    """将 Agent 产生的 domain events 编排为 StreamEvent 流。"""
    
    def __init__(self, ...):
        # ... 现有代码 ...
        self._skill_injector = SkillInjector(skill_registry)
        self._activated_skills: list[str] = []  # 记录已激活的技能
    
    async def run(self) -> AsyncGenerator[StreamEvent, None]:
        # 1) start
        yield make_event(...)
        
        try:
            # 1.5) 关键词匹配技能（在 Agent 调用前）
            triggered_skills = await self._skill_injector.match_and_activate_skills(
                message=self._user_message,
                agent_type=self._agent_type,
                mode=self._mode,
                emitter=emitter,
            )
            
            # 将触发的技能内容注入到当前对话上下文
            if triggered_skills:
                skill_context = skill_registry.build_skill_context(triggered_skills)
                chat_context.inject_skill_context(skill_context)
            
            # 2) Agent 处理
            # ... 现有代码 ...
            
            while True:
                evt = await domain_queue.get()
                evt_type = evt.get("type")
                
                # ... 现有事件处理 ...
                
                # 新增：技能事件处理
                if evt_type == StreamEventType.SKILL_ACTIVATED.value:
                    skill_name = payload.get("skill_name")
                    self._activated_skills.append(skill_name)
                
                yield make_event(...)
```

### 3.6 load_skill 工具（AI 主动调用）

```python
# backend/app/services/agent/tools/skill.py

from langchain_core.tools import tool

def create_load_skill_tool(config: AgentConfig, registry: SkillRegistry):
    """创建 load_skill 工具"""
    
    available_skills = registry.get_skills_for_agent(
        agent_type=config.type,
        mode=config.mode,
    )
    
    # 过滤掉 always_apply（已自动注入）
    loadable_skills = [s for s in available_skills if not s.always_apply]
    
    if not loadable_skills:
        return None
    
    skill_descriptions = "\n".join([
        f"- **{s.name}**: {s.description}"
        for s in loadable_skills
    ])
    
    @tool
    async def load_skill(skill_name: str) -> str:
        """加载专业技能的提示词和上下文。
        
        当你需要处理特定类型的问题时，可以加载对应的技能来获取专业指导。
        
        可用技能：
        {skill_descriptions}
        
        Args:
            skill_name: 要加载的技能名称
            
        Returns:
            技能的提示词和上下文内容
        """
        skill = next(
            (s for s in loadable_skills if s.name == skill_name),
            None
        )
        if not skill:
            return f"技能 '{skill_name}' 不存在或不可用"
        
        # 发送 skill.loaded 事件
        # （通过 context 获取 emitter）
        
        return skill.content
    
    # 动态更新 docstring
    load_skill.__doc__ = load_skill.__doc__.format(
        skill_descriptions=skill_descriptions
    )
    
    return load_skill
```

---

## 4. 前端实现设计

### 4.1 新增类型定义

```typescript
// frontend/types/chat.ts

// 新增事件类型
export type SkillEventType = "skill.activated" | "skill.loaded";

// 更新 ChatEventType
export type ChatEventType =
  | StreamLevelEventType
  | LLMCallBoundaryEventType
  | LLMCallInternalEventType
  | ToolCallEventType
  | DataEventType
  | PostProcessEventType
  | SupportEventType
  | SupervisorEventType
  | SkillEventType;  // 新增

// 新增 Payload
export interface SkillActivatedPayload {
  skill_id: string;
  skill_name: string;
  trigger_type: "keyword" | "intent" | "manual";
  trigger_keyword?: string;
}

export interface SkillLoadedPayload {
  skill_id: string;
  skill_name: string;
  skill_category: string;
}

// 更新 ChatEventPayload
export type ChatEventPayload =
  | MetaStartPayload
  | TextDeltaPayload
  // ... 现有 ...
  | SkillActivatedPayload  // 新增
  | SkillLoadedPayload     // 新增
  | Record<string, unknown>;

// 更新 ChatEvent 联合类型
export type ChatEvent =
  // ... 现有 ...
  | (ChatEventBase & { type: "skill.activated"; payload: SkillActivatedPayload })
  | (ChatEventBase & { type: "skill.loaded"; payload: SkillLoadedPayload })
  // ...
```

### 4.2 新增 Timeline Item 类型

```typescript
// frontend/lib/timeline-utils.ts

// 新增技能激活 Item
export interface SkillActivatedItem {
  type: "skill.activated";
  id: string;
  turnId: string;
  skillId: string;
  skillName: string;
  triggerType: "keyword" | "intent" | "manual";
  triggerKeyword?: string;
  ts: number;
}

// 更新 TimelineItem 联合类型
export type TimelineItem =
  | UserMessageItem
  | LLMCallClusterItem
  | ToolCallItem
  | AssistantProductsItem
  | AssistantTodosItem
  | ContextSummarizedItem
  | ErrorItem
  | SkillActivatedItem;  // 新增
```

### 4.3 技能激活组件（轻提示）

```tsx
// frontend/components/features/chat/timeline/TimelineSkillActivatedItem.tsx

"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SkillActivatedItem } from "@/lib/timeline-utils";

interface TimelineSkillActivatedItemProps {
  item: SkillActivatedItem;
}

export function TimelineSkillActivatedItem({ item }: TimelineSkillActivatedItemProps) {
  return (
    <div className="flex justify-center py-2">
      <div
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full",
          "bg-purple-50 text-purple-700 text-xs font-medium",
          "dark:bg-purple-900/30 dark:text-purple-300",
          "border border-purple-200 dark:border-purple-800",
          "animate-in fade-in-0 zoom-in-95 duration-300"
        )}
      >
        <Sparkles className="h-3 w-3" />
        <span>已启用「{item.skillName}」技能</span>
        {item.triggerKeyword && (
          <span className="opacity-60">· 关键词: {item.triggerKeyword}</span>
        )}
      </div>
    </div>
  );
}
```

### 4.4 更新 Timeline 工具映射

```typescript
// frontend/lib/timeline-utils.ts

/** 工具名称中文映射 */
const TOOL_LABEL_MAP: Record<string, string> = {
  search_products: "商品搜索",
  get_product_details: "商品详情",
  filter_by_price: "价格筛选",
  compare_products: "商品对比",
  guide_user: "用户引导",
  load_skill: "加载技能",  // 新增
};
```

### 4.5 更新事件处理

```typescript
// frontend/lib/timeline-utils.ts

export function processEvent(state: TimelineState, event: ChatEvent): TimelineState {
  const { type } = event;
  const now = Date.now();
  const turnId = state.activeTurn.turnId;

  switch (type) {
    // ... 现有 case ...

    case "skill.activated": {
      const payload = event.payload as SkillActivatedPayload;
      const skillItem: SkillActivatedItem = {
        type: "skill.activated",
        id: `skill:${payload.skill_id}:${event.seq}`,
        turnId,
        skillId: payload.skill_id,
        skillName: payload.skill_name,
        triggerType: payload.trigger_type,
        triggerKeyword: payload.trigger_keyword,
        ts: now,
      };
      return insertItem(state, skillItem);
    }

    case "skill.loaded": {
      // AI 主动加载的技能，作为 tool.end 的子事件处理
      // 或者也可以显示为轻提示
      const payload = event.payload as SkillLoadedPayload;
      // ... 处理逻辑 ...
      return state;
    }

    // ...
  }
}
```

### 4.6 更新 ChatContent 渲染

```tsx
// frontend/components/features/chat/ChatContent.tsx

import { TimelineSkillActivatedItem } from "./timeline/TimelineSkillActivatedItem";

function renderTimelineItem(item: TimelineItem) {
  switch (item.type) {
    // ... 现有 case ...

    case "skill.activated":
      return (
        <TimelineSkillActivatedItem key={item.id} item={item} />
      );
    
    // ...
  }
}
```

---

## 5. 渲染效果预览

### 5.1 关键词触发（轻提示）

```
┌─────────────────────────────────────────────────────────┐
│ 用户: 帮我对比一下 iPhone 15 和 Samsung S24            │
└─────────────────────────────────────────────────────────┘

                 ┌────────────────────────────┐
                 │ ✨ 已启用「商品对比专家」技能 │
                 └────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🤖 好的，我来帮你对比这两款手机...                      │
│                                                         │
│ | 维度     | iPhone 15 | Samsung S24 |                 │
│ |---------|-----------|-------------|                  │
│ | 价格    | ¥5,999    | ¥5,499      |                  │
│ | ...     | ...       | ...         |                  │
└─────────────────────────────────────────────────────────┘
```

### 5.2 AI 主动调用（可选显示为工具卡片）

```
┌─────────────────────────────────────────────────────────┐
│ 用户: 这个产品有什么常见问题？                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🔧 ✓ 加载技能 · FAQ精准匹配 · 12ms                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🤖 根据 FAQ 知识库，这个产品的常见问题有...            │
└─────────────────────────────────────────────────────────┘
```

### 5.3 静默注入（无展示）

always_apply 技能直接注入 system prompt，用户无感知。

---

## 6. 配置选项

### 6.1 Agent 配置扩展

```python
# backend/app/schemas/agent.py

class AgentConfig(BaseModel):
    # ... 现有字段 ...
    
    # 技能相关配置
    enable_skill_tool: bool = False          # 是否启用 load_skill 工具
    show_skill_activation: bool = True       # 是否显示技能激活提示
    skill_activation_style: Literal[
        "badge",    # 轻提示 Badge
        "card",     # 工具卡片
        "hidden"    # 隐藏
    ] = "badge"
```

### 6.2 前端配置

```typescript
// frontend/stores/chat-settings.ts

interface ChatSettings {
  // ... 现有配置 ...
  
  // 技能展示配置
  showSkillActivation: boolean;  // 是否显示技能激活提示
  skillActivationStyle: "badge" | "card" | "hidden";
}
```

---

## 7. 实现步骤

### Phase 1: 后端事件支持（1 天）
1. 新增 `skill.activated` / `skill.loaded` 事件类型
2. 实现 `SkillInjector` 服务
3. 修改 `ChatStreamOrchestrator` 支持技能事件

### Phase 2: 前端渲染（1 天）
1. 新增类型定义
2. 实现 `TimelineSkillActivatedItem` 组件
3. 更新事件处理和渲染逻辑

### Phase 3: load_skill 工具（0.5 天）
1. 实现 `create_load_skill_tool`
2. 集成到 Agent 工厂

### Phase 4: 测试和优化（0.5 天）
1. 单元测试
2. 集成测试
3. UI 细节调优

---

## 8. 总结

| 维度 | 设计决策 |
|-----|---------|
| **always_apply 技能** | 静默注入 system prompt，无事件 |
| **关键词触发技能** | 发送 `skill.activated` 事件，显示轻提示 Badge |
| **AI 主动调用技能** | 使用 `load_skill` 工具，可选显示为工具卡片或隐藏 |
| **前端组件** | 新增 `TimelineSkillActivatedItem`，居中显示紫色 Badge |
| **配置灵活性** | 支持 badge/card/hidden 三种展示风格 |
