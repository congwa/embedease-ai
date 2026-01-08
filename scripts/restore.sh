#!/bin/bash

# ========================================
# EmbedAI Agent 数据恢复脚本
# ========================================

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <备份文件>"
    echo "示例: $0 ./backups/embedai-backup-20240108_120000.tar.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "开始恢复数据..."
echo "备份文件: $BACKUP_FILE"
echo ""

# 确认操作
read -p "⚠️  此操作将覆盖现有数据，是否继续？(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

# 停止服务
echo "停止服务..."
docker compose -f docker-compose.prod.yml down

# 解压备份文件
TEMP_DIR=$(mktemp -d)
echo "解压备份文件到临时目录: $TEMP_DIR"
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# 恢复后端数据
if [ -f "$TEMP_DIR"/backend-data-*.tar.gz ]; then
    echo "恢复后端数据..."
    docker run --rm -v embedai-agent_backend_data:/app/data -v "$TEMP_DIR":/backup alpine sh -c "cd / && tar -xzf /backup/backend-data-*.tar.gz"
fi

# 恢复 Qdrant 数据
if [ -f "$TEMP_DIR"/qdrant-data-*.tar.gz ]; then
    echo "恢复 Qdrant 数据..."
    docker run --rm -v embedai-agent_qdrant_data:/data -v "$TEMP_DIR":/backup alpine sh -c "cd / && tar -xzf /backup/qdrant-data-*.tar.gz"
fi

# 恢复配置文件
if [ -f "$TEMP_DIR"/config-*.tar.gz ]; then
    echo "恢复配置文件..."
    tar -xzf "$TEMP_DIR"/config-*.tar.gz -C .
fi

# 恢复 PostgreSQL 数据
if [ -f "$TEMP_DIR"/postgres-*.sql ]; then
    echo "恢复 PostgreSQL 数据..."
    docker compose -f docker-compose.prod.yml up -d postgres
    sleep 5
    docker compose -f docker-compose.prod.yml exec -T postgres psql -U embedai embedai < "$TEMP_DIR"/postgres-*.sql
fi

# 清理临时目录
rm -rf "$TEMP_DIR"

# 启动服务
echo "启动服务..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "恢复完成！"
echo "请等待服务启动，然后访问 http://localhost:3000"
