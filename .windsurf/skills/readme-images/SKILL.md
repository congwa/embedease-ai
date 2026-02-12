---
name: readme-images
description: Handle README.md image references for GitHub and Gitee platforms. Use when writing or converting README.md files that contain images, ensuring correct image paths for each platform. GitHub READMEs use Qiniu cloud URLs (via qiniu-upload skill), Gitee READMEs use local relative image paths.
---

# Readme Images

README.md 中的图片引用规范。

## 核心规则

**所有图片统一使用相对路径**，GitHub 和 Gitee 共用同一份 README，无需区分平台、无需转换。

```markdown
![功能截图](./docs/screenshots/feature.avif)
![架构图](./images/architecture.png)
```

## 工作原理

- **GitHub**：自动解析为 `https://raw.githubusercontent.com/user/repo/branch/path`
- **Gitee**：自动解析为 `https://gitee.com/user/repo/raw/branch/path`

两个平台都官方支持相对路径，零外部依赖，最稳定。

## 图片目录规范

```
project/
├── README.md
├── docs/
│   └── screenshots/       # 推荐：功能截图
│       ├── feature.avif
│       └── demo.webp
└── images/                # 备选：通用图片
    └── logo.png
```

## 必须遵守

1. **图片文件必须提交到仓库** — 两个平台都需要文件存在
2. **使用相对路径** — 以 `./` 开头或直接写相对路径
3. **不使用绝对 URL** — 不用 CDN、不用 raw.githubusercontent.com、不用七牛云
4. **图片需压缩** — 遵循 `image-compress` skill 规则，确保图片 < 100KB
5. **推荐格式** — avif > webp > png > jpg

## 禁止的写法

```markdown
<!-- ❌ 七牛云 URL -->
![图片](http://qiniu.biomed168.com/pic/screenshot.png)

<!-- ❌ GitHub Raw URL -->
![图片](https://raw.githubusercontent.com/user/repo/main/images/pic.png)

<!-- ❌ jsdelivr CDN -->
![图片](https://cdn.jsdelivr.net/gh/user/repo@main/images/pic.png)
```
