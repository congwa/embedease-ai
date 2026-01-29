---
name: auto-screenshot
description: 自动截屏功能页面。当用户需要更新项目文档截图、生成功能演示图、或需要记录当前 UI 状态时触发。
触发关键词：截屏、screenshot、截图、更新文档图片、生成演示图
---

# 自动截屏 Skill

自动运行项目并对主要功能页面进行全屏截屏，保存到 `/docs/screenshots` 目录。

## 前置条件

1. **前端服务已启动**（`http://localhost:3000`）
2. **安装 Playwright**（首次使用需安装）

## 执行流程

### 步骤 1：检查前端服务

```bash
# 如果前端服务未启动，先启动
cd frontend && pnpm dev
```

### 步骤 2：安装依赖（首次使用）

```bash
# 安装 Playwright
pnpm add -D playwright @types/node tsx

# 安装浏览器（首次使用）
npx playwright install chromium
```

### 步骤 3：运行截屏脚本

```bash
npx tsx .windsurf/skills/auto-screenshot/scripts/screenshot.ts
```

## 截屏页面列表

| 路径 | 文件名 | 描述 |
|------|--------|------|
| `/` | landing-page.png | 产品落地页 |
| `/chat` | chat-interface.png | 用户聊天界面 |
| `/admin` | admin-dashboard.png | 管理后台仪表盘 |
| `/admin/quick-setup` | quick-setup.png | 快速配置向导 |
| `/admin/agents` | agent-list.png | Agent 列表 |
| `/admin/single` | single-mode.png | 单 Agent 模式配置 |
| `/admin/multi` | multi-mode.png | 编排模式配置 |
| `/admin/settings` | settings.png | 系统设置 |
| `/admin/settings/mode` | mode-settings.png | 模式设置 |
| `/admin/skills` | skills-list.png | 技能列表 |
| `/support` | support-workbench.png | 客服工作台 |

## 输出文件

```
docs/
├── screenshots/
│   ├── landing-page.png
│   ├── chat-interface.png
│   ├── admin-dashboard.png
│   └── ...
└── SCREENSHOTS.md          # 截图索引文件
```

## 配置选项

可在 `scripts/screenshot.ts` 中修改：

```typescript
const CONFIG = {
  baseUrl: 'http://localhost:3000',  // 服务地址
  outputDir: './docs/screenshots',    // 输出目录
  viewport: { width: 1920, height: 1080 },  // 视口大小
  timeout: 30000,  // 超时时间
};
```

## 添加新页面

在 `PAGES` 数组中添加：

```typescript
{ path: '/admin/new-page', name: 'new-page', description: '新页面描述' },
```

## 注意事项

1. **需要登录的页面**：脚本目前不处理登录状态，如需截取需要登录的页面，需要修改脚本添加登录逻辑
2. **动态内容**：脚本会等待页面加载完成，但动态加载的数据可能显示为空
3. **深色模式**：默认使用系统主题，如需指定可在脚本中添加主题切换逻辑
