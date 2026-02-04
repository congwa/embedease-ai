---
description: 创建 Git Tag 并推送（带版本一致性检查）
---

# 创建版本发布工作流

此工作流用于完整的版本发布流程：收集变更 → 更新文档 → 更新版本 → 打 Tag → 推送。

---

## 第一步：收集变更日志

1. 获取上一个 Tag 到现在的所有提交：
```bash
git log $(git describe --tags --abbrev=0 2>/dev/null || echo HEAD~50)..HEAD --oneline --no-merges
```

2. 将提交按类型分类整理：
   - `feat:` → **Added** 
   - `fix:` → **Fixed**
   - `refactor:` / `perf:` → **Changed**
   - `docs:` → **Documentation**
   - `chore:` / `build:` → 可选忽略或放入 **Other**

3. 生成变更摘要，准备写入 CHANGELOG.md

---

## 第二步：更新 CHANGELOG.md

1. 读取当前版本号：
```bash
python3 -c "import re; print(re.search(r'^version = \"([^\"]+)\"', open('backend/pyproject.toml').read(), re.MULTILINE).group(1))"
```

2. 在 `CHANGELOG.md` 顶部（第 7 行后）添加新版本条目，格式：
```markdown
## [x.x.x] - YYYY-MM-DD

### 核心亮点

简要描述本版本的主要变更。

### Added
- 新功能描述

### Changed
- 变更描述

### Fixed
- 修复描述
```

3. **确认 CHANGELOG.md 已包含即将发布的版本号**，否则停止流程。

---

## 第三步：更新 SDK 变更说明

每个 SDK 包目录下应有 `CHANGELOG.md`，记录该包的变更：

- `frontend/packages/chat-sdk/CHANGELOG.md`
- `frontend/packages/chat-sdk-react/CHANGELOG.md`
- `backend/packages/langgraph-agent-kit/CHANGELOG.md`

如果 SDK 包在本版本有变更，需同步更新对应的 CHANGELOG。

格式与主 CHANGELOG 一致。

---

## 第四步：更新版本号

1. 运行版本更新脚本（根据变更类型选择）：
```bash
# 补丁版本（bug fix）
python3 update_version.py patch

# 次版本（新功能）
python3 update_version.py minor

# 主版本（破坏性变更）
python3 update_version.py major
```

// turbo
2. 验证版本一致性：
```bash
python3 update_version.py --check
```

**如果检查失败（返回码非 0），停止流程并修复版本不一致问题。**

---

## 第五步：提交版本变更

1. 确认所有变更：
```bash
git status
```

2. 提交版本更新：
```bash
git add -A
git commit -m "chore: release v{VERSION}"
git push
```

---

## 第六步：创建并推送 Tag

// turbo
1. 获取当前版本号：
```bash
python3 -c "import re; print(re.search(r'^version = \"([^\"]+)\"', open('backend/pyproject.toml').read(), re.MULTILINE).group(1))"
```

2. 创建 Tag：
```bash
git tag -a v{VERSION} -m "Release v{VERSION}"
```

3. 推送 Tag：
```bash
git push origin v{VERSION}
```

---

## 快速发布示例

```bash
# 1. 查看变更
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# 2. 更新 CHANGELOG.md（手动编辑）
# 3. 更新版本号
python3 update_version.py minor

# 4. 验证
python3 update_version.py --check

# 5. 提交
git add -A
git commit -m "chore: release v0.2.0"
git push

# 6. 打 Tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

---

## 检查清单

发布前确认：

- [ ] 所有提交已整理到 CHANGELOG.md
- [ ] SDK 包的 CHANGELOG.md 已更新（如有变更）
- [ ] `python3 update_version.py --check` 通过
- [ ] 工作区干净（无未提交更改）
- [ ] 代码已推送到远程
- [ ] CI 测试通过

---

## 注意事项

- **版本检查必须通过**才能打 Tag
- Tag 名称格式：`v{major}.{minor}.{patch}`
- CHANGELOG 日期格式：`YYYY-MM-DD`
- 遵循 [Semantic Versioning](https://semver.org/) 规范
