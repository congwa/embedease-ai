---
name: skill-maintenance
description: Skill 内容维护检查。每次修改代码后自动触发，检查现有 skill 文档是否需要同步更新。
触发场景：
- 修改前端代码结构（新增/删除/重命名目录、组件、模块）
- 修改后端代码结构（新增/删除/重命名路由、服务、模型）
- 修改配置文件（navigation.ts、labels.ts 等）
- 修改路由体系
- 修改状态管理
alwaysApply: true（始终应用）
---

# Skill 内容维护检查

每次代码修改后，检查现有 skill 文档是否需要同步更新。

## 现有 Skill 清单

| Skill | 路径 | 关注的代码变更 |
|-------|------|----------------|
| `frontend-architecture` | `.windsurf/skills/frontend-architecture/` | 前端目录结构、组件、路由、状态管理、API 封装 |
| `frontend-component-design` | `.windsurf/skills/frontend-component-design/` | 组件设计规范、命名规范、代码风格 |
| `backend-architecture` | `.windsurf/skills/backend-architecture/` | 后端模块、路由、服务、模型 |
| `run-tests` | `.windsurf/skills/run-tests/` | 测试相关代码、测试命令 |

## 检查触发条件

### 前端架构 Skill 需要更新的情况

1. **目录结构变更**
   - 新增/删除/重命名 `frontend/` 下的一级目录
   - 新增/删除/重命名 `frontend/app/admin/` 下的功能模块
   - 新增/删除/重命名 `frontend/components/` 下的组件分类

2. **路由体系变更**
   - 新增/删除/修改 Agent 配置入口路由
   - 修改 `AgentDetailLayout` 或 `getAgentTabs()` 逻辑
   - 新增/删除侧边栏菜单项

3. **状态管理变更**
   - 新增/删除/重命名 Zustand store
   - 修改 store 的核心接口

4. **配置文件变更**
   - 修改 `lib/config/navigation.ts` 导航结构
   - 修改 `lib/config/labels.ts` 标签映射结构
   - 新增/删除 `lib/config/` 下的配置文件

5. **公共组件变更**
   - 新增/删除 `components/admin/` 下的公共组件
   - 修改组件导出 `components/admin/index.ts`

### 后端架构 Skill 需要更新的情况

1. **模块结构变更**
   - 新增/删除/重命名 `backend/app/` 下的一级目录
   - 新增/删除服务模块 `backend/app/services/`

2. **路由变更**
   - 新增/删除/重命名 API 路由 `backend/app/routers/`
   - 修改路由前缀或版本

3. **模型变更**
   - 新增/删除数据模型 `backend/app/models/`
   - 修改核心模型字段

4. **服务变更**
   - 新增/删除核心服务
   - 修改服务的主要接口

## 检查流程

代码修改完成后，执行以下检查：

```
1. 识别本次修改涉及的文件和目录
2. 对照上述触发条件，判断是否需要更新 skill
3. 如果需要更新：
   a. 读取对应 skill 的 SKILL.md
   b. 对比代码变更，识别需要同步的内容
   c. 更新 SKILL.md 中的相关章节
4. 告知用户更新了哪些 skill 以及更新内容
```

## 输出格式

检查完成后，输出以下格式的报告：

```
## Skill 维护检查报告

### 本次代码变更
- 修改了 xxx
- 新增了 xxx
- 删除了 xxx

### Skill 更新情况
- ✅ frontend-architecture: 无需更新
- ⚠️ backend-architecture: 需要更新
  - 原因：新增了 xxx 服务
  - 更新内容：在「服务模块」章节添加 xxx
```

## 注意事项

1. **增量更新**：只更新变更涉及的部分，不要重写整个 skill
2. **保持一致性**：更新内容的格式与现有内容保持一致
3. **避免冗余**：如果变更是临时的或实验性的，可以暂不更新 skill
4. **主动询问**：如果不确定是否需要更新，询问用户
