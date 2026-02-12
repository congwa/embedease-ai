---
name: frontend-architecture
description: 前端代码架构上下文。此技能在每次对话开始时自动触发，提供项目前端的模块化架构概览。
包含：目录结构、核心模块、状态管理、路由体系、组件分层、API 封装、配置管理等组件的介绍。
触发条件：alwaysApply: true（始终应用）
---

# EmbedEase AI 前端架构

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Next.js | 16.x | App Router 框架 |
| React | 19.x | UI 库 |
| TypeScript | 5.x | 类型系统 |
| TailwindCSS | 4.x | 样式方案 |
| shadcn/ui | - | 组件库 |
| Zustand | - | 状态管理 |
| SWR | - | 数据请求 |

## 目录结构

```
frontend/
├── app/                      # Next.js App Router 页面
│   ├── admin/               # 管理后台（主要业务）
│   │   ├── agents/         # Agent 中心（完整配置）
│   │   ├── single/         # 单 Agent 模式配置
│   │   ├── multi/          # 编排模式配置
│   │   ├── settings/       # 系统设置
│   │   ├── quick-setup/    # 快速配置向导
│   │   └── [feature]/      # 其他功能模块
│   ├── chat/                # 用户聊天界面
│   ├── support/             # 客服工作台
│   └── api/                 # API Routes
│
├── components/               # 组件库
│   ├── ui/                  # shadcn/ui 基础组件
│   ├── admin/               # 管理后台公共组件
│   │   ├── sidebars/       # 侧边栏组件
│   │   ├── agents/         # Agent 相关组件
│   │   └── index.ts        # 统一导出
│   ├── features/            # 功能性组件
│   │   ├── chat/           # 聊天相关
│   │   ├── config/         # 配置展示组件
│   │   └── embed/          # 嵌入式组件
│   ├── rich-editor/         # 富文本编辑器
│   └── prompt-kit/          # 提示词组件
│
├── lib/                      # 核心逻辑库
│   ├── api/                 # API 请求封装
│   ├── config/              # 配置和映射
│   │   ├── labels.ts       # 标签映射（英文→中文）
│   │   ├── navigation.ts   # 导航配置
│   │   └── agent-tabs.ts   # Agent Tab 配置
│   ├── hooks/               # 业务 hooks
│   └── timeline/            # 时间线逻辑
│
├── stores/                   # Zustand 状态管理
│   ├── mode-store.ts        # 系统模式（single/supervisor）
│   ├── agent-store.ts       # Agent 状态
│   ├── chat-store.ts        # 聊天状态
│   └── index.ts             # 统一导出
│
├── hooks/                    # 全局 React hooks
│   ├── use-features.ts      # 功能开关
│   ├── use-support-*.ts     # 客服相关
│   └── use-user-websocket.ts # WebSocket
│
├── types/                    # TypeScript 类型定义
│   ├── chat.ts              # 聊天类型
│   ├── effective-config.ts  # 运行态配置
│   └── quick-setup.ts       # 快速配置
│
└── embed/                    # 嵌入式 SDK
```

## 核心模块详解

### 1. 路由体系

项目有三个 Agent 配置入口，服务不同场景：

| 路由 | 场景 | 特点 |
|------|------|------|
| `/admin/agents/[agentId]` | Agent 中心 | 完整功能，包含运行态预览、多 Agent 编排 |
| `/admin/single/agents/[agentId]` | 单 Agent 模式 | 日常配置入口，精简 Tab |
| `/admin/multi/agents/[agentId]` | 编排模式 | 子 Agent 配置，包含路由配置 |

三个路由共享 `AgentDetailLayout` 组件和 `getAgentTabs()` 配置函数。

### 2. 状态管理（Zustand）

```typescript
// stores/mode-store.ts - 系统模式
type SystemMode = "single" | "supervisor";
interface ModeState {
  mode: SystemMode;
  activeAgentId: string | null;
  supervisorConfig: SupervisorConfig | null;
  switchMode: (mode: SystemMode) => Promise<boolean>;
}

// stores/agent-store.ts - Agent 状态
interface AgentState {
  agents: Agent[];
  activeAgent: () => Agent | undefined;
  activateAgent: (agentId: string) => Promise<void>;
}

// stores/chat-store.ts - 聊天状态
interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
}
```

### 3. API 封装（lib/api/）

所有 API 请求通过 `lib/api/` 统一封装：

```typescript
// lib/api/client.ts - 基础请求
export async function apiRequest<T>(endpoint: string, options?: RequestInit): Promise<T>

// lib/api/agents.ts - Agent API
export async function getAgent(agentId: string): Promise<Agent>
export async function updateAgent(agentId: string, data: AgentUpdate): Promise<Agent>
export async function getAgentEffectiveConfig(agentId: string): Promise<EffectiveConfig>

// lib/api/admin.ts - 管理 API
export async function getSystemStats(): Promise<SystemStats>
export async function getFeatureFlags(): Promise<FeatureFlags>
```

### 4. 配置管理（lib/config/）

```typescript
// lib/config/labels.ts - 标签映射
export const MIDDLEWARE_LABELS: Record<string, MiddlewareInfo>
export const TOOL_CATEGORY_LABELS: Record<string, ToolCategoryInfo>
export function getMiddlewareLabel(name: string): MiddlewareInfo

// lib/config/navigation.ts - 导航配置
export const singleModeMainNav: NavItem[]
export const multiModeMainNav: NavItem[]
export const systemNavItems: NavItem[]
export function getNavigationConfig(mode: SystemMode): NavigationConfig

// lib/config/agent-tabs.ts - Agent Tab 配置
export function getAgentTabs(options: AgentTabOptions): TabConfig[]
```

### 5. 组件分层

```
┌─────────────────────────────────────────────────┐
│                    Pages                         │
│  (app/admin/*/page.tsx - 页面协调逻辑)           │
├─────────────────────────────────────────────────┤
│               Feature Components                 │
│  (components/features/* - 功能性组件)            │
│  (components/admin/* - 管理后台组件)             │
├─────────────────────────────────────────────────┤
│                 UI Components                    │
│  (components/ui/* - shadcn/ui 基础组件)          │
├─────────────────────────────────────────────────┤
│                    Hooks                         │
│  (hooks/*, lib/hooks/* - 状态和副作用)           │
├─────────────────────────────────────────────────┤
│                   Stores                         │
│  (stores/* - Zustand 全局状态)                   │
├─────────────────────────────────────────────────┤
│                  API Layer                       │
│  (lib/api/* - 请求封装)                          │
└─────────────────────────────────────────────────┘
```

### 6. 侧边栏体系

根据系统模式显示不同侧边栏：

```
┌─────────────────┐    ┌─────────────────┐
│  SingleSidebar  │    │  MultiSidebar   │
│  (单 Agent 模式) │    │  (编排模式)      │
├─────────────────┤    ├─────────────────┤
│ 📊 仪表盘       │    │ 📊 仪表盘       │
│ 🟢 Agent 配置   │    │ 🟣 编排配置     │
│ ────────────── │    │ 🔀 路由策略     │
│ ⚙️ 系统管理     │    │ 🤖 子 Agent     │
│ ────────────── │    │ ────────────── │
│ ✨ 快速配置     │    │ ⚙️ 系统管理     │
│ 🟣 配置编排模式 │    │ ────────────── │
│ 💬 客服工作台   │    │ ✨ 快速配置     │
└─────────────────┘    │ 🟢 配置单Agent  │
                       │ 💬 客服工作台   │
                       └─────────────────┘
```

### 7. 公共组件（components/admin/）

| 组件 | 用途 |
|------|------|
| `AgentDetailLayout` | Agent 详情页统一布局 |
| `PageHeader` | 页面标题组件 |
| `LoadingState` | 加载状态 |
| `ErrorAlert` | 错误提示 |
| `StatusBadge` | 状态徽章 |
| `StatCard` | 统计卡片 |
| `ConfirmDialog` | 确认对话框 |
| `ModeIndicator` | 模式指示器 |
| `PromptViewer/Editor` | 提示词查看/编辑 |

## 关键设计模式

### 1. 配置外置

所有中文标签、枚举映射存放在 `lib/config/labels.ts`：

```typescript
// 不要这样写（硬编码）
<span>滑动窗口</span>

// 应该这样写（配置外置）
import { getMiddlewareLabel } from "@/lib/config/labels";
<span>{getMiddlewareLabel("SlidingWindow").label}</span>
```

### 2. 路径别名

始终使用 `@/` 别名，禁止相对路径：

```typescript
// ✅ 正确
import { Button } from "@/components/ui/button";

// ❌ 错误
import { Button } from "../../components/ui/button";
```

### 3. 组件导出

公共组件通过 `index.ts` 统一导出：

```typescript
// components/admin/index.ts
export { AgentDetailLayout } from "./agent-detail-layout";
export { LoadingState } from "./loading-state";
export { PageHeader } from "./page-header";
// ...

// 使用时
import { AgentDetailLayout, LoadingState, PageHeader } from "@/components/admin";
```

### 4. Hooks 命名

- 业务 hooks：`use[业务名][动作]`
- 例如：`useAgentDetail`, `useAgentStore`, `useSupportStats`

## 修改代码时的检查清单

修改前端代码时，确认以下事项：

1. **路径别名**：使用 `@/` 而非相对路径
2. **配置外置**：中文标签来自 `lib/config/labels.ts`
3. **组件复用**：检查是否有现成组件可用
4. **类型定义**：新类型放入 `types/` 目录
5. **API 封装**：请求函数放入 `lib/api/` 目录
6. **状态管理**：全局状态使用 Zustand stores
7. **导航配置**：菜单项通过 `lib/config/navigation.ts` 管理
