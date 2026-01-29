---
name: frontend-component-design
description: 前端组件设计规范与最佳实践。在编写任何前端代码（React/Next.js 组件、页面、hooks）时自动触发。确保代码复用性、封装性、单一职责原则。触发场景包括创建新的前端组件或页面、重构现有前端代码、添加新功能到前端、任何涉及 frontend 目录的代码修改。此技能始终生效。
---

# 前端组件设计规范

确保前端代码的复用性、封装性和可维护性。

## 核心原则

### 1. 单一职责原则
- 每个文件只包含一个组件
- 每个组件只负责一个业务功能
- 组件代码不超过 **500 行**，超过则拆分

### 2. 组件拆分规则

```
# 拆分时机判断
if 组件 > 500 行:
    拆分为子组件
if 相同代码出现 >= 2 次:
    抽取为公共组件
if 业务逻辑复杂:
    抽取为 hooks
if 配置数据多:
    抽取为配置文件
```

### 3. 目录结构规范

```
frontend/
├── components/           # 公共组件
│   ├── ui/              # shadcn 基础组件
│   └── admin/           # 业务公共组件
├── app/                 # 页面
│   └── admin/
│       └── [feature]/
│           ├── page.tsx         # 主页面（协调逻辑）
│           └── components/      # 页面私有组件（可选）
├── lib/
│   ├── api/             # API 请求函数
│   ├── config/          # 配置和映射
│   └── hooks/           # 公共 hooks
├── hooks/               # 全局 hooks
└── types/               # 类型定义
```

### 4. 配置外置原则

将以下内容抽取到 `lib/config/` 目录：
- **标签映射** → `labels.ts` (英文→中文)
- **枚举常量** → `constants.ts`
- **表单配置** → `forms.ts`
- **主题配置** → `theme.ts`

示例：
```typescript
// lib/config/labels.ts
export const MIDDLEWARE_LABELS = {
  MemoryOrchestration: { label: "记忆编排", desc: "..." },
  // ...
};
export function getMiddlewareLabel(name: string) {
  return MIDDLEWARE_LABELS[name] || { label: name, desc: "" };
}
```

### 5. Hooks 抽取规则

抽取为 hook 的时机：
- 状态逻辑复杂（>5 个 useState）
- 数据获取逻辑
- 副作用逻辑复杂
- 相同逻辑在多处使用

命名规范：`use[业务名][动作]`
```typescript
// lib/hooks/use-agents.ts
export function useAgentDetail({ agentId }: { agentId: string }) {
  const [agent, setAgent] = useState<Agent | null>(null);
  // ...
  return { agent, isLoading, error, refresh };
}
```

### 6. 导入路径规范

始终使用 `@/` 别名，避免相对路径：
```typescript
// ✅ 正确
import { Button } from "@/components/ui/button";
import { getAgentEffectiveConfig } from "@/lib/api/agents";

// ❌ 错误
import { Button } from "../../components/ui/button";
```

## 编码前规划清单

编写前端代码前，必须回答：

1. **组件边界**：这个组件的职责是什么？是否单一？
2. **复用性**：是否有已存在的类似组件可复用？
3. **配置外置**：是否有硬编码的中文/配置需要抽取？
4. **文件大小**：预估代码行数，是否需要拆分？
5. **命名规范**：组件/文件命名是否清晰表达业务含义？

## 代码审查要点

完成编码后，检查：

- [ ] 单文件不超过 500 行
- [ ] 无重复代码（相同代码不超过 2 处）
- [ ] 所有中文标签来自配置文件
- [ ] 使用 `@/` 路径别名
- [ ] 组件职责单一
- [ ] 复杂逻辑已抽取为 hooks
