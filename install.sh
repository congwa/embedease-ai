#!/bin/bash

# ========================================
# EmbedAI Agent 一键安装脚本
# ========================================
# 自动检测环境、配置参数、启动服务
# 适合不懂代码的用户直接运行

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 Docker 和 Docker Compose
check_docker() {
    print_header "检查 Docker 环境"
    
    if ! command_exists docker; then
        print_error "未检测到 Docker，请先安装 Docker"
        print_info "访问 https://docs.docker.com/get-docker/ 下载安装"
        exit 1
    fi
    
    if ! docker compose version >/dev/null 2>&1; then
        print_error "未检测到 Docker Compose，请升级 Docker 到最新版本"
        exit 1
    fi
    
    print_success "Docker 环境检查通过"
    docker --version
    docker compose version
}

# 检查端口占用
check_ports() {
    print_header "检查端口占用"
    
    local ports=(3000 8000 6333 5432)
    local port_names=("前端" "后端" "Qdrant" "PostgreSQL")
    local occupied_ports=()
    
    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local name=${port_names[$i]}
        
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":$port.*LISTEN"; then
            print_warning "端口 $port ($name) 已被占用"
            occupied_ports+=("$port")
        else
            print_success "端口 $port ($name) 可用"
        fi
    done
    
    if [ ${#occupied_ports[@]} -gt 0 ]; then
        echo ""
        print_warning "以下端口被占用: ${occupied_ports[*]}"
        read -p "是否继续安装？Docker 会尝试使用这些端口 (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "安装已取消"
            exit 0
        fi
    fi
}

# 配置向量数据库
configure_vector_db() {
    print_header "配置向量数据库"
    
    echo "请选择向量数据库方案："
    echo "1) 使用 Docker 内置的 Qdrant（推荐，无需额外配置）"
    echo "2) 使用已有的 Qdrant 服务"
    echo "3) 使用其他向量数据库（需要手动配置）"
    
    read -p "请输入选项 [1-3] (默认: 1): " vector_choice
    vector_choice=${vector_choice:-1}
    
    case $vector_choice in
        1)
            print_success "将使用 Docker 内置的 Qdrant"
            QDRANT_HOST="qdrant"
            QDRANT_PORT="6333"
            USE_DOCKER_QDRANT=true
            ;;
        2)
            print_info "配置外部 Qdrant 服务"
            read -p "请输入 Qdrant 主机地址 (默认: localhost): " qdrant_host
            QDRANT_HOST=${qdrant_host:-localhost}
            
            read -p "请输入 Qdrant 端口 (默认: 6333): " qdrant_port
            QDRANT_PORT=${qdrant_port:-6333}
            
            USE_DOCKER_QDRANT=false
            print_success "已配置外部 Qdrant: $QDRANT_HOST:$QDRANT_PORT"
            ;;
        3)
            print_warning "使用其他向量数据库需要手动修改配置文件"
            print_info "安装完成后请编辑 .env.docker 文件"
            QDRANT_HOST="qdrant"
            QDRANT_PORT="6333"
            USE_DOCKER_QDRANT=true
            ;;
        *)
            print_error "无效的选项"
            exit 1
            ;;
    esac
}

# 配置 LLM 提供商
configure_llm() {
    print_header "配置 LLM 提供商"
    
    echo "请选择 LLM 提供商："
    echo "1) SiliconFlow（推荐，国内访问快，价格便宜）"
    echo "2) OpenAI"
    echo "3) DeepSeek"
    echo "4) Anthropic (Claude)"
    echo "5) 其他兼容 OpenAI API 的提供商"
    
    read -p "请输入选项 [1-5] (默认: 1): " llm_choice
    llm_choice=${llm_choice:-1}
    
    case $llm_choice in
        1)
            LLM_PROVIDER="siliconflow"
            LLM_BASE_URL="https://api.siliconflow.cn/v1"
            LLM_CHAT_MODEL="moonshotai/Kimi-K2-Thinking"
            EMBEDDING_MODEL="Qwen/Qwen3-Embedding-8B"
            EMBEDDING_DIMENSION="4096"
            RERANK_MODEL="Qwen/Qwen3-Reranker-8B"
            
            print_info "请访问 https://cloud.siliconflow.cn 获取 API Key"
            ;;
        2)
            LLM_PROVIDER="openai"
            LLM_BASE_URL="https://api.openai.com/v1"
            LLM_CHAT_MODEL="gpt-4"
            EMBEDDING_MODEL="text-embedding-3-large"
            EMBEDDING_DIMENSION="3072"
            RERANK_MODEL=""
            
            print_info "请访问 https://platform.openai.com 获取 API Key"
            ;;
        3)
            LLM_PROVIDER="deepseek"
            LLM_BASE_URL="https://api.deepseek.com/v1"
            LLM_CHAT_MODEL="deepseek-chat"
            EMBEDDING_MODEL="deepseek-embedding"
            EMBEDDING_DIMENSION="1536"
            RERANK_MODEL=""
            
            print_info "请访问 https://platform.deepseek.com 获取 API Key"
            ;;
        4)
            LLM_PROVIDER="anthropic"
            LLM_BASE_URL="https://api.anthropic.com/v1"
            LLM_CHAT_MODEL="claude-3-5-sonnet-20241022"
            EMBEDDING_MODEL="text-embedding-3-large"
            EMBEDDING_DIMENSION="3072"
            RERANK_MODEL=""
            
            print_info "请访问 https://console.anthropic.com 获取 API Key"
            print_warning "注意：Anthropic 不提供 Embedding，需要配置其他提供商"
            ;;
        5)
            print_info "配置自定义提供商"
            read -p "请输入提供商名称: " LLM_PROVIDER
            read -p "请输入 API Base URL: " LLM_BASE_URL
            read -p "请输入聊天模型名称: " LLM_CHAT_MODEL
            read -p "请输入 Embedding 模型名称: " EMBEDDING_MODEL
            read -p "请输入 Embedding 维度: " EMBEDDING_DIMENSION
            RERANK_MODEL=""
            ;;
        *)
            print_error "无效的选项"
            exit 1
            ;;
    esac
    
    echo ""
    read -p "请输入 LLM API Key: " LLM_API_KEY
    
    if [ -z "$LLM_API_KEY" ]; then
        print_error "API Key 不能为空"
        exit 1
    fi
    
    print_success "LLM 配置完成"
}

# 配置服务端口
configure_ports() {
    print_header "配置服务端口"
    
    read -p "前端服务端口 (默认: 3000): " frontend_port
    FRONTEND_PORT=${frontend_port:-3000}
    
    read -p "后端服务端口 (默认: 8000): " api_port
    API_PORT=${api_port:-8000}
    
    print_success "端口配置完成"
}

# 生成配置文件
generate_config() {
    print_header "生成配置文件"
    
    # 备份旧配置
    if [ -f .env.docker ]; then
        cp .env.docker .env.docker.backup.$(date +%Y%m%d_%H%M%S)
        print_info "已备份旧配置文件"
    fi
    
    # 生成新配置
    cat > .env.docker << EOF
# ========================================
# Docker 部署配置文件
# ========================================
# 此文件由 install.sh 自动生成于 $(date)
# 如需修改配置，请重新运行 install.sh 或手动编辑此文件

# ========================================
# LLM 提供商配置
# ========================================
LLM_PROVIDER=$LLM_PROVIDER
LLM_API_KEY=$LLM_API_KEY
LLM_BASE_URL=$LLM_BASE_URL
LLM_CHAT_MODEL=$LLM_CHAT_MODEL

# ========================================
# Embeddings 配置
# ========================================
EMBEDDING_PROVIDER=$LLM_PROVIDER
EMBEDDING_MODEL=$EMBEDDING_MODEL
EMBEDDING_DIMENSION=$EMBEDDING_DIMENSION

# ========================================
# Rerank 配置
# ========================================
RERANK_ENABLED=true
RERANK_MODEL=$RERANK_MODEL
RERANK_TOP_N=5
RERANK_INSTRUCTION=根据查询对商品进行相关性排序

# ========================================
# Qdrant 向量数据库配置
# ========================================
QDRANT_HOST=$QDRANT_HOST
QDRANT_PORT=$QDRANT_PORT
QDRANT_COLLECTION=products

# ========================================
# PostgreSQL 数据库配置
# ========================================
POSTGRES_USER=embedai
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
POSTGRES_DB=embedai
POSTGRES_PORT=5432

# ========================================
# 数据库配置
# ========================================
DATABASE_PATH=/app/data/app.db
CHECKPOINT_DB_PATH=/app/data/checkpoints.db

# ========================================
# 文本处理配置
# ========================================
CHUNK_SIZE=800
CHUNK_OVERLAP=100

# ========================================
# 服务配置
# ========================================
API_HOST=0.0.0.0
API_PORT=$API_PORT
FRONTEND_PORT=$FRONTEND_PORT
BACKEND_HOST=localhost
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# CORS 跨域配置
CORS_ORIGINS=http://localhost:$FRONTEND_PORT,http://localhost:80

# ========================================
# 日志配置
# ========================================
LOG_LEVEL=INFO
LOG_MODE=detailed
LOG_FILE=/app/logs/app.log
LOG_FILE_ROTATION=10 MB
LOG_FILE_RETENTION=7 days

# ========================================
# 聊天模式配置
# ========================================
CHAT_MODE=natural

# ========================================
# Agent 配置
# ========================================
AGENT_SERIALIZE_TOOLS=true
AGENT_TODO_ENABLED=true
AGENT_TOOL_LIMIT_ENABLED=true
AGENT_TOOL_LIMIT_THREAD=100
AGENT_TOOL_LIMIT_RUN=20
AGENT_TOOL_LIMIT_EXIT_BEHAVIOR=continue
AGENT_TOOL_RETRY_ENABLED=true
AGENT_TOOL_RETRY_MAX_RETRIES=2
AGENT_TOOL_RETRY_BACKOFF_FACTOR=2.0
AGENT_TOOL_RETRY_INITIAL_DELAY=1.0
AGENT_TOOL_RETRY_MAX_DELAY=60.0
AGENT_SUMMARIZATION_ENABLED=true
AGENT_SUMMARIZATION_TRIGGER_MESSAGES=50
AGENT_SUMMARIZATION_KEEP_MESSAGES=20
AGENT_SUMMARIZATION_TRIM_TOKENS=4000

# ========================================
# 商品库画像配置
# ========================================
CATALOG_PROFILE_ENABLED=true
CATALOG_PROFILE_TTL_SECONDS=600
CATALOG_PROFILE_TOP_CATEGORIES=3

# ========================================
# 记忆系统配置
# ========================================
MEMORY_ENABLED=true
MEMORY_STORE_ENABLED=true
MEMORY_STORE_DB_PATH=/app/data/memory_store.db
MEMORY_FACT_ENABLED=true
MEMORY_FACT_DB_PATH=/app/data/facts.db
MEMORY_FACT_COLLECTION=memory_facts
MEMORY_FACT_SIMILARITY_THRESHOLD=0.5
MEMORY_FACT_MAX_RESULTS=10
MEMORY_GRAPH_ENABLED=true
MEMORY_GRAPH_FILE_PATH=/app/data/knowledge_graph.jsonl
MEMORY_ORCHESTRATION_ENABLED=true
MEMORY_ASYNC_WRITE=true

# ========================================
# 网站爬取模块配置
# ========================================
CRAWLER_ENABLED=false
CRAWLER_HEADLESS=true
CRAWLER_MAX_HTML_LENGTH=50000
CRAWLER_DEFAULT_DELAY=1.0
CRAWLER_DEFAULT_MAX_DEPTH=3
CRAWLER_DEFAULT_MAX_PAGES=500

# ========================================
# 默认 Agent 配置
# ========================================
DEFAULT_AGENTS_BOOTSTRAP_ENABLED=true
DEFAULT_AGENTS_OVERRIDE_POLICY=skip

# ========================================
# 模型能力配置
# ========================================
ENV_JSON_DIR=.env.json
MODELS_DEV_ENABLED=true
MODELS_DEV_API_URL=https://models.dev/api.json
MODELS_DEV_TIMEOUT_SECONDS=10.0
MODELS_DEV_CACHE_TTL_SECONDS=86400.0
EOF
    
    print_success "配置文件已生成: .env.docker"
}

# 启动服务
start_services() {
    print_header "启动服务"
    
    print_info "正在拉取 Docker 镜像..."
    docker compose -f docker-compose.prod.yml pull
    
    print_info "正在构建应用镜像..."
    docker compose -f docker-compose.prod.yml build
    
    print_info "正在启动服务..."
    docker compose -f docker-compose.prod.yml up -d
    
    print_success "服务启动成功！"
}

# 等待服务就绪
wait_for_services() {
    print_header "等待服务就绪"
    
    print_info "等待后端服务启动..."
    local max_attempts=60
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$API_PORT/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            break
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_warning "后端服务启动超时，请检查日志"
        print_info "运行 'docker compose -f docker-compose.prod.yml logs backend' 查看日志"
    fi
    
    echo ""
    print_info "等待前端服务启动..."
    sleep 5
    
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        print_success "前端服务已就绪"
    else
        print_warning "前端服务可能还在启动中"
    fi
}

# 导入示例数据
import_sample_data() {
    print_header "导入示例数据"
    
    read -p "是否导入示例商品数据？(y/n, 默认: y): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]] || [ -z "$REPLY" ]; then
        print_info "正在导入示例数据..."
        
        if docker compose -f docker-compose.prod.yml exec -T backend uv run python scripts/import_products.py; then
            print_success "示例数据导入成功"
        else
            print_warning "示例数据导入失败，可以稍后手动导入"
            print_info "运行: docker compose -f docker-compose.prod.yml exec backend uv run python scripts/import_products.py"
        fi
    else
        print_info "跳过示例数据导入"
    fi
}

# 显示访问信息
show_access_info() {
    print_header "安装完成"
    
    echo -e "${GREEN}🎉 恭喜！EmbedAI Agent 已成功安装并启动${NC}"
    echo ""
    echo "访问地址："
    echo -e "  前端界面: ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "  后端 API: ${BLUE}http://localhost:$API_PORT${NC}"
    echo -e "  API 文档: ${BLUE}http://localhost:$API_PORT/docs${NC}"
    echo ""
    echo "常用命令："
    echo "  查看服务状态: docker compose -f docker-compose.prod.yml ps"
    echo "  查看日志:     docker compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务:     docker compose -f docker-compose.prod.yml down"
    echo "  重启服务:     docker compose -f docker-compose.prod.yml restart"
    echo ""
    echo "配置文件："
    echo "  .env.docker - 环境配置"
    echo ""
    
    if [ "$USE_DOCKER_QDRANT" = true ]; then
        echo -e "${YELLOW}注意：${NC}向量数据库 Qdrant 运行在 Docker 容器中"
        echo "  访问地址: http://localhost:6333/dashboard"
    fi
    
    echo ""
    print_info "如需帮助，请查看 README_DOCKER.md"
}

# 主函数
main() {
    clear
    
    print_header "EmbedAI Agent 一键安装向导"
    
    echo "欢迎使用 EmbedAI Agent！"
    echo "本脚本将帮助您快速部署完整的商品推荐 Agent 系统"
    echo ""
    echo "安装过程包括："
    echo "  1. 检查 Docker 环境"
    echo "  2. 配置向量数据库"
    echo "  3. 配置 LLM 提供商"
    echo "  4. 生成配置文件"
    echo "  5. 启动所有服务"
    echo ""
    
    read -p "按 Enter 键开始安装..." -r
    
    # 执行安装步骤
    check_docker
    check_ports
    configure_vector_db
    configure_llm
    configure_ports
    generate_config
    start_services
    wait_for_services
    import_sample_data
    show_access_info
    
    print_success "安装完成！"
}

# 运行主函数
main
