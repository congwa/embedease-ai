---
name: sdk-sync
description: embedease-sdk 代码同步指南。当修改 SDK 代码后需要同步到独立仓库时触发。
触发场景：
- 修改 frontend/packages/chat-sdk 或 chat-sdk-react
- 修改 backend/packages/langgraph-agent-kit
- 需要发布新版本 SDK
alwaysApply: false
---

# embedease-sdk 代码同步指南

本项目是 SDK 的源头仓库，SDK 代码同时维护在：
1. **本项目**：`frontend/packages/` 和 `backend/packages/`
2. **独立仓库**：https://github.com/congwa/embedease-sdk

## SDK 目录结构

```
embedease-ai/
├── frontend/packages/
│   ├── chat-sdk/           # 前端核心 SDK
│   └── chat-sdk-react/     # React 封装
└── backend/packages/
    └── langgraph-agent-kit/ # 后端 Python SDK
```

## 同步流程

### 1. 修改 SDK 代码

在本项目中直接修改 SDK 代码：
- `frontend/packages/chat-sdk/src/`
- `frontend/packages/chat-sdk-react/src/`
- `backend/packages/langgraph-agent-kit/src/`

### 2. 更新版本号

修改以下文件的版本号：
- `frontend/packages/chat-sdk/package.json` → `version`
- `frontend/packages/chat-sdk-react/package.json` → `version`
- `backend/packages/langgraph-agent-kit/pyproject.toml` → `version`

**注意**：chat-sdk 和 chat-sdk-react 保持版本号一致

### 3. 更新 CHANGELOG

在各包的 `CHANGELOG.md` 中添加变更记录：

```markdown
## [x.x.x] - YYYY-MM-DD

### Added
- 新增 xxx 功能

### Changed
- 修改 xxx 行为

### Fixed
- 修复 xxx 问题
```

### 4. 同步到独立仓库

```bash
# 假设 embedease-sdk 仓库在同级目录
SDK_REPO="../embedease-sdk"

# 复制前端 SDK
cp -r frontend/packages/chat-sdk/* $SDK_REPO/frontend/chat-sdk/
cp -r frontend/packages/chat-sdk-react/* $SDK_REPO/frontend/chat-sdk-react/

# 复制后端 SDK
cp -r backend/packages/langgraph-agent-kit/* $SDK_REPO/backend/langgraph-agent-kit/

# 提交到 SDK 仓库
cd $SDK_REPO
git add .
git commit -m "chore: 同步 SDK v0.x.x"
git tag v0.x.x
git push origin main
git push origin v0.x.x
```

## 版本号规范

遵循 SemVer 语义化版本：

| 变更类型 | 版本号变化 | 示例 |
|----------|-----------|------|
| Bug 修复 | PATCH +1 | 0.1.16 → 0.1.17 |
| 新功能（向后兼容） | MINOR +1 | 0.1.16 → 0.2.0 |
| 破坏性变更 | MAJOR +1 | 0.1.16 → 1.0.0 |

## 同步检查清单

- [ ] SDK 代码修改完成
- [ ] 版本号已更新（三处）
- [ ] CHANGELOG 已更新
- [ ] 本项目已提交
- [ ] 同步到 embedease-sdk 仓库并打 Tag
