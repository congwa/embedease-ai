#!/bin/bash

# ========================================
# EmbedAI Agent 快速启动脚本
# ========================================
# 用于已完成安装的用户快速启动服务

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}EmbedAI Agent 快速启动${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否已安装
if [ ! -f .env.docker ]; then
    echo -e "${BLUE}检测到首次运行，启动安装向导...${NC}"
    ./install.sh
    exit 0
fi

# 启动服务
echo -e "${BLUE}正在启动服务...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo ""
echo -e "${GREEN}服务启动成功！${NC}"
echo ""
echo "访问地址："
echo -e "  前端界面: ${BLUE}http://localhost:3000${NC}"
echo -e "  后端 API: ${BLUE}http://localhost:8000${NC}"
echo -e "  API 文档: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "常用命令："
echo "  查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo "  停止服务: docker compose -f docker-compose.prod.yml down"
echo "  重启服务: docker compose -f docker-compose.prod.yml restart"
echo ""
