---
name: release
description: |
  发版流程 - 仔细阅读上个版本到现在版本的内容，把更改功能放到项目CHANGELOG.md目录下，处理README图片引用，然后提交且推送所有源码到GitHub和Gitee双平台，再之后打tag
  触发条件：用户要求发版、发布、release、打tag
---

# 发版 Skill

## 依赖的 Skills

- **readme-images** — 确认 README 图片使用相对路径
- **image-compress** — 确认图片 < 100KB

## 发版流程

### 1. 检查当前版本状态

```bash
cat CHANGELOG.md
git describe --tags --abbrev=0
```

### 2. 分析版本变更

```bash
git log --oneline --decorate --graph $(git describe --tags --abbrev=0)..HEAD
```

### 3. 更新 CHANGELOG.md

确定新版本号（遵循语义化版本），添加新版本条目：

```markdown
## [X.Y.Z] - YYYY-MM-DD

### 核心亮点

简要描述本版本的重要特性或改进

### Added
- 新功能列表

### Changed
- 修改的功能列表

### Fixed
- 修复的问题列表
```

### 4. 检查 README 图片

遵循 `readme-images` skill 规则：
- 确认所有图片使用**相对路径**（如 `./docs/screenshots/xx.avif`）
- 不使用七牛云 URL、GitHub Raw URL 或 CDN

遵循 `image-compress` skill 规则：
- 确认所有图片 < 100KB

```bash
# 检查图片大小
bash .windsurf/skills/image-compress/scripts/check_compress.sh
```

### 5. 提交并推送（双平台，一次提交）

```bash
git add .
git commit -m "release: v[版本号] 发布"

# 推送到 GitHub
git push github main

# 推送到 Gitee
git push gitee main
```

> 注意：由于 README 使用相对路径，两个平台共用同一份，无需分别处理。

### 6. 创建版本标签（双平台）

```bash
git tag -a v[版本号] -m "Release v[版本号]"
git push github v[版本号]
git push gitee v[版本号]
```

## 版本号规则

遵循 [Semantic Versioning](https://semver.org/)：

- **MAJOR**：不兼容的 API 修改
- **MINOR**：向下兼容的功能性新增
- **PATCH**：向下兼容的问题修正

## 多子项目处理

如果项目包含多个子项目（如 frontend、backend 等）：

1. **主项目 CHANGELOG**：记录整体项目变更
2. **子项目 CHANGELOG**：记录子模块特定变更
3. **版本同步**：确保相关子项目版本号保持一致

## 远程仓库设置

```bash
# 查看远程仓库配置
git remote -v

# 添加远程仓库（如果不存在）
git remote add github https://github.com/[username]/[repository].git
git remote add gitee https://gitee.com/[username]/[repository].git
```

## 发布前检查清单

- [ ] 所有代码已提交
- [ ] CHANGELOG.md 已更新
- [ ] 版本号符合语义化版本规范
- [ ] README 图片使用相对路径（遵循 readme-images skill）
- [ ] 图片大小 < 100KB（遵循 image-compress skill）
- [ ] 远程仓库已配置（GitHub + Gitee）
- [ ] 标签已创建并推送到双平台
- [ ] 双平台仓库已同步

## 特殊项目说明

### Tauri 应用（如 wdm）

发版时额外需要：

1. **同步更新版本号**（3 处）：
   - `package.json` → `"version"`
   - `src-tauri/tauri.conf.json` → `"version"`
   - `src-tauri/Cargo.toml` → `version`
2. **构建应用**：`npm run tauri:build`
3. **上传 DMG 到 GitHub/Gitee Release**

### 仅 GitHub 的项目（如 cong_wa_skills）

跳过 Gitee 相关步骤，仅推送到 GitHub。

## 常用命令

```bash
git describe --tags --abbrev=0       # 查看最新标签
git tag --sort=-version:refname      # 查看所有标签
git tag -d v[版本号]                  # 删除本地标签
git push github --delete v[版本号]   # 删除远程标签
```
