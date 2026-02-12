#!/bin/bash
# 检查并压缩超过 100KB 的图片
# 用法: bash check_compress.sh [目录...]
# 默认扫描 docs/ 和 images/

set -e

THRESHOLD=102400  # 100KB in bytes
DIRS="${@:-docs images}"
FOUND=0

echo "🔍 扫描图片文件（阈值: 100KB）..."

for dir in $DIRS; do
    [ -d "$dir" ] || continue
    while IFS= read -r -d '' file; do
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt "$THRESHOLD" ]; then
            kb=$(( size / 1024 ))
            echo "⚠️  ${file} (${kb}KB) 超过 100KB"
            FOUND=$((FOUND + 1))
        fi
    done < <(find "$dir" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.webp" -o -name "*.avif" -o -name "*.gif" -o -name "*.bmp" -o -name "*.tiff" \) -print0)
done

if [ "$FOUND" -eq 0 ]; then
    echo "✅ 所有图片均在 100KB 以内"
else
    echo ""
    echo "❌ 发现 ${FOUND} 个图片超过 100KB"
    echo ""
    echo "压缩建议："
    echo "  # png → avif（体积最小）"
    echo "  ffmpeg -i input.png -c:v libaom-av1 -crf 30 -still-picture 1 output.avif"
    echo ""
    echo "  # png → webp"
    echo "  ffmpeg -i input.png -quality 80 output.webp"
    echo ""
    echo "  # 缩小尺寸"
    echo "  sips --resampleWidth 1200 image.png"
    exit 1
fi
