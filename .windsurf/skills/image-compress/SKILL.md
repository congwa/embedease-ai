---
name: image-compress
description: 图片压缩检查规则。当添加或修改 README 引用的图片时自动触发。检查图片是否超过 100KB，超出则压缩。推荐使用 avif/webp 格式。触发场景：添加新图片到仓库、更新 README 中的截图、发版前检查。
---

# Image Compress

README 引用的图片不得超过 **100KB**。

## 检查规则

1. 扫描 README.md 中所有 `![](path)` 引用的图片文件
2. 检查每个文件大小，超过 100KB 的必须压缩
3. 推荐格式优先级：**avif > webp > png > jpg**

## 检查命令

```bash
# 查找 docs/ 和 images/ 下超过 100KB 的图片
find docs/ images/ -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.avif" -o -name "*.gif" \) -size +100k
```

## 压缩方式

### macOS 内置 sips（png/jpg）

```bash
# 缩小尺寸（保持宽度 1200px 以内）
sips --resampleWidth 1200 image.png

# 转为 jpg 并降低质量
sips -s format jpeg -s formatOptions 80 image.png --out image.jpg
```

### ffmpeg（推荐，支持 avif/webp）

```bash
# png → avif（推荐，体积最小）
ffmpeg -i input.png -c:v libaom-av1 -crf 30 -still-picture 1 output.avif

# png → webp
ffmpeg -i input.png -quality 80 output.webp

# 批量转换
for f in docs/screenshots/*.png; do
  ffmpeg -i "$f" -c:v libaom-av1 -crf 30 -still-picture 1 "${f%.png}.avif"
done
```

### 使用 scripts/check_compress.sh

```bash
bash .windsurf/skills/image-compress/scripts/check_compress.sh
```

## 压缩后

1. 更新 README.md 中的图片路径（扩展名可能变化）
2. 删除旧的大图片文件
3. 确认所有图片 < 100KB
