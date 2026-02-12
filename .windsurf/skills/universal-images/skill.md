---
name: universal-images
description: 通用图片处理方案 - 官方推荐使用相对路径实现GitHub和Gitee双平台完美显示，不依赖第三方CDN
---

# Universal Images Skill

## 官方推荐方案：相对路径（最稳妥）

### 为什么相对路径是最佳选择

1. **官方推荐**：GitHub和Gitee都官方支持相对路径
2. **零依赖**：不依赖任何第三方CDN或外部服务
3. **自动适配**：平台自动解析到对应的资源服务器
4. **最稳定**：不会因为网络问题或CDN故障而失效

### 正确的写法

```markdown
# 推荐格式（带./前缀）
![图片描述](./images/pic.png)
![截图](./docs/screenshots/demo.png)

# 简化格式（不带./前缀）
![图片描述](images/pic.png)
![截图](docs/screenshots/demo.png)
```

### 工作原理

- **GitHub查看时**：自动指向 `https://raw.githubusercontent.com/user/repo/main/images/pic.png`
- **Gitee查看时**：自动指向 `https://gitee.com/user/repo/raw/main/images/pic.png`

### 前提条件

**重要**：图片文件必须提交到仓库中，确保两个平台都有相同的文件结构。

```
project/
├── README.md
├── images/
│   ├── pic.png
│   └── screenshot.jpg
└── docs/
    └── screenshots/
        └── demo.png
```

## 其他方案（备选）

### 方案2: jsdelivr CDN（网络不稳定时慎用）

```markdown
![图片](https://cdn.jsdelivr.net/gh/user/repo@main/images/pic.png)
```

### 方案3: GitHub Raw URL（部分地区无法访问）

```markdown
![图片](https://raw.githubusercontent.com/user/repo/main/images/pic.png)
```

### 方案4: Gitee Raw URL

```markdown
![图片](https://gitee.com/user/repo/raw/main/images/pic.png)
```

## 自动化处理

### 检测当前平台并转换

```bash
# 自动检测git远程仓库并转换图片路径
python3 .windsurf/skills/universal-images/scripts/auto_convert.py

# 官方推荐：转换为相对路径
python3 .windsurf/skills/universal-images/scripts/auto_convert.py --platform relative

# 其他转换选项（备选方案）
python3 .windsurf/skills/universal-images/scripts/auto_convert.py --platform jsdelivr-cdn
python3 .windsurf/skills/universal-images/scripts/auto_convert.py --platform github-raw
python3 .windsurf/skills/universal-images/scripts/auto_convert.py --platform gitee-raw
```

### 批量处理多个项目

```bash
# 处理所有项目（使用官方推荐的相对路径）
for project in mobile-mcp Skill-Know embedease-ai embedease-sdk; do
    cd /Users/wang/code/$project
    python3 .windsurf/skills/universal-images/scripts/auto_convert.py --platform relative
    git add README.md
    git commit -m "feat: 使用官方推荐的相对路径格式，确保双平台图片显示稳定"
    git push github main
    git push gitee main
done
```

## 最佳实践

### 推荐配置

1. **使用相对路径** - 官方推荐，最稳定
2. **图片文件存放在仓库中** - 单一数据源
3. **确保文件结构一致** - 两个平台相同的目录结构

### 图片目录规范

```
project/
├── README.md
├── images/
│   ├── screenshot1.png
│   ├── screenshot2.jpg
│   └── demo.gif
└── docs/
    └── images/
        └── diagram.png
```

### 转换规则

| 原路径 | 相对路径（推荐） | GitHub Raw URL | jsdelivr CDN |
|--------|----------------|----------------|-------------|
| `images/pic.png` | `images/pic.png` | `https://raw.githubusercontent.com/user/repo/main/images/pic.png` | `https://cdn.jsdelivr.net/gh/user/repo@main/images/pic.png` |
| `docs/images/diagram.png` | `docs/images/diagram.png` | `https://raw.githubusercontent.com/user/repo/main/docs/images/diagram.png` | `https://cdn.jsdelivr.net/gh/user/repo@main/docs/images/diagram.png` |

## 脚本功能

### auto_convert.py

- 自动检测Git远程仓库
- 扫描README.md中的图片引用
- 根据指定平台转换图片路径
- 支持批量处理多个文件

### 使用示例

```bash
# 检测当前平台并自动转换
python3 scripts/auto_convert.py

# 转换为GitHub Raw URL格式
python3 scripts/auto_convert.py --platform github-raw

# 转换为相对路径格式
python3 scripts/auto_convert.py --platform relative

# 预览转换结果（不修改文件）
python3 scripts/auto_convert.py --dry-run
```

## 优势

1. **官方支持** - GitHub和Gitee都官方推荐相对路径
2. **零网络依赖** - 不依赖任何外部CDN服务
3. **自动适配** - 平台自动解析到正确的资源地址
4. **最稳定可靠** - 不会因为网络问题或服务故障失效
5. **维护简单** - 只需确保图片文件在仓库中

## 注意事项

1. **图片文件必须提交到仓库**
2. **两个平台的文件结构必须保持一致**
3. **相对路径区分大小写**
4. **大文件建议压缩后提交**
