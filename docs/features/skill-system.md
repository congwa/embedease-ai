# Agent 技能系统

为智能体提供可扩展的专业技能能力，支持自定义创建和 AI 智能生成。

## 功能概述

技能系统允许用户为 Agent 配置专业领域知识，增强其在特定场景下的表现。

### 核心特性

- **系统内置技能** - 5 个预设技能，不可修改删除
- **用户自定义技能** - 完全可编辑、可删除
- **AI 智能生成** - 描述需求，AI 自动生成结构化技能
- **关键词触发** - 用户消息匹配关键词时自动激活
- **静默注入** - `always_apply` 技能自动注入系统提示词

## 技能类型

| 类型 | 说明 | 可编辑 |
|-----|-----|--------|
| `system` | 系统内置 | ❌ |
| `user` | 用户创建 | ✅ |
| `ai` | AI 生成 | ✅ |

## 技能分类

| 分类 | 用途 |
|-----|-----|
| `prompt` | 提示词增强 - 改善回复质量和风格 |
| `retrieval` | 检索增强 - 优化知识检索策略 |
| `tool` | 工具扩展 - 增强工具调用能力 |
| `workflow` | 工作流 - 复杂任务编排 |

## 系统内置技能

1. **商品对比专家** - 多维度商品对比分析
2. **预算规划师** - 预算约束下的推荐
3. **FAQ 精准匹配** - FAQ 知识库精准回复
4. **知识库深度检索** - 多轮对话信息综合
5. **客服情绪安抚** - 用户情绪识别与安抚

## 触发机制

### 静默注入（always_apply）

对于标记为 `always_apply=true` 的技能，在 Agent 初始化时自动注入到系统提示词，用户无感知。

### 关键词触发

当用户消息包含技能配置的触发关键词时，系统发送 `skill.activated` 事件，前端显示轻提示：

```
                 ┌────────────────────────────┐
                 │ ✨ 已启用「商品对比专家」技能 │
                 └────────────────────────────┘
```

## API 接口

### 技能管理

| 方法 | 路径 | 说明 |
|-----|-----|-----|
| GET | `/api/v1/admin/skills` | 获取技能列表 |
| POST | `/api/v1/admin/skills` | 创建技能 |
| GET | `/api/v1/admin/skills/{id}` | 获取技能详情 |
| PUT | `/api/v1/admin/skills/{id}` | 更新技能 |
| DELETE | `/api/v1/admin/skills/{id}` | 删除技能 |

### AI 生成

| 方法 | 路径 | 说明 |
|-----|-----|-----|
| POST | `/api/v1/admin/skills/generate` | AI 生成技能 |
| POST | `/api/v1/admin/skills/{id}/refine` | AI 优化技能 |

### 系统技能

| 方法 | 路径 | 说明 |
|-----|-----|-----|
| GET | `/api/v1/admin/skills/system/list` | 获取系统技能 |
| POST | `/api/v1/admin/skills/system/init` | 初始化系统技能 |

## 前端页面

| 路径 | 功能 |
|-----|-----|
| `/admin/skills` | 技能列表（筛选、搜索、删除） |
| `/admin/skills/create` | 创建新技能 |
| `/admin/skills/generate` | AI 生成技能 |
| `/admin/skills/[id]` | 技能详情/编辑 |

## 使用示例

### 创建技能

```json
{
  "name": "价格敏感分析",
  "description": "分析用户价格敏感度，提供合适价位推荐",
  "category": "prompt",
  "content": "## 价格敏感分析\n\n当用户提到价格相关词汇时...",
  "trigger_keywords": ["便宜", "贵", "价格", "预算", "性价比"],
  "always_apply": false,
  "applicable_agents": ["product"]
}
```

### AI 生成技能

```json
{
  "description": "我需要一个帮助用户对比多个商品的技能，能够分析商品的优劣势，列出对比表格",
  "category": "prompt",
  "applicable_agents": ["product"]
}
```

## 技术实现

### 后端

- `app/models/skill.py` - 数据模型
- `app/schemas/skill.py` - Pydantic Schema
- `app/services/skill/` - 业务服务
  - `service.py` - CRUD 操作
  - `generator.py` - AI 生成
  - `registry.py` - 运行时缓存
  - `injector.py` - 技能注入
- `app/routers/skills.py` - API 路由

### 前端

- `lib/api/skills.ts` - API 客户端
- `app/admin/skills/` - 管理页面
- `components/features/chat/timeline/TimelineSkillActivatedItem.tsx` - 激活提示组件

## 测试覆盖

- Schema 测试：26 个用例
- Service 测试：20 个用例
- Router 测试：18 个用例
- Injector 测试：9 个用例

**总计：73 个测试用例全部通过**
