#!/bin/bash

# ========================================
# EmbedAI Agent 数据备份脚本
# ========================================

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/embedai-backup-$TIMESTAMP.tar.gz"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

echo "开始备份数据..."
echo "备份时间: $(date)"
echo "备份文件: $BACKUP_FILE"
echo ""

# 备份后端数据
echo "备份后端数据..."
docker compose -f docker-compose.prod.yml exec -T backend tar -czf - /app/data > "$BACKUP_DIR/backend-data-$TIMESTAMP.tar.gz"

# 备份 Qdrant 数据
echo "备份 Qdrant 数据..."
docker run --rm -v embedai-agent_qdrant_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar -czf "/backup/qdrant-data-$TIMESTAMP.tar.gz" /data

# 备份 PostgreSQL 数据（如果使用）
if docker compose -f docker-compose.prod.yml ps postgres | grep -q "Up"; then
    echo "备份 PostgreSQL 数据..."
    docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U embedai embedai > "$BACKUP_DIR/postgres-$TIMESTAMP.sql"
fi

# 备份配置文件
echo "备份配置文件..."
tar -czf "$BACKUP_DIR/config-$TIMESTAMP.tar.gz" .env.docker docker-compose.prod.yml

# 合并所有备份
echo "合并备份文件..."
tar -czf "$BACKUP_FILE" -C "$BACKUP_DIR" \
    "backend-data-$TIMESTAMP.tar.gz" \
    "qdrant-data-$TIMESTAMP.tar.gz" \
    "config-$TIMESTAMP.tar.gz" \
    $([ -f "$BACKUP_DIR/postgres-$TIMESTAMP.sql" ] && echo "postgres-$TIMESTAMP.sql" || echo "")

# 清理临时文件
rm -f "$BACKUP_DIR/backend-data-$TIMESTAMP.tar.gz"
rm -f "$BACKUP_DIR/qdrant-data-$TIMESTAMP.tar.gz"
rm -f "$BACKUP_DIR/config-$TIMESTAMP.tar.gz"
rm -f "$BACKUP_DIR/postgres-$TIMESTAMP.sql"

echo ""
echo "备份完成！"
echo "备份文件: $BACKUP_FILE"
echo "文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo "恢复命令: ./scripts/restore.sh $BACKUP_FILE"
