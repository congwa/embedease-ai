#!/bin/bash

# ========================================
# EmbedAI Agent 更新脚本
# ========================================

set -e

echo "开始更新 EmbedAI Agent..."
echo ""

# 备份当前数据
echo "1. 备份当前数据..."
./scripts/backup.sh

# 拉取最新代码
echo ""
echo "2. 拉取最新代码..."
git pull

# 重新构建镜像
echo ""
echo "3. 重新构建镜像..."
docker compose -f docker-compose.prod.yml build

# 停止旧服务
echo ""
echo "4. 停止旧服务..."
docker compose -f docker-compose.prod.yml down

# 启动新服务
echo ""
echo "5. 启动新服务..."
docker compose -f docker-compose.prod.yml up -d

# 等待服务就绪
echo ""
echo "6. 等待服务就绪..."
sleep 10

# 检查服务状态
echo ""
echo "7. 检查服务状态..."
docker compose -f docker-compose.prod.yml ps

echo ""
echo "更新完成！"
echo "访问地址: http://localhost:3000"
echo ""
echo "如遇问题，可使用备份恢复："
echo "  ./scripts/restore.sh ./backups/embedai-backup-*.tar.gz"
