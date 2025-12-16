#!/bin/bash

# EmbedAI Agent 版本管理脚本
# 自动递增版本号并更新相关文件

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 获取当前版本号
get_current_version() {
    # 从 backend/pyproject.toml 读取版本
    if [ -f "backend/pyproject.toml" ]; then
        grep '^version = ' backend/pyproject.toml | sed 's/version = "\(.*\)"/\1/'
    elif [ -f "pyproject.toml" ]; then
        grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
    else
        log_error "找不到版本文件 (pyproject.toml)"
        exit 1
    fi
}

# 递增版本号
increment_version() {
    local version=$1
    local increment_type=${2:-"patch"}  # major, minor, patch

    # 解析版本号
    IFS='.' read -ra VERSION_PARTS <<< "$version"
    local major=${VERSION_PARTS[0]}
    local minor=${VERSION_PARTS[1]}
    local patch=${VERSION_PARTS[2]}

    case $increment_type in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
        *)
            log_error "无效的递增类型: $increment_type (支持: major, minor, patch)"
            exit 1
            ;;
    esac

    echo "$major.$minor.$patch"
}

# 更新 backend/pyproject.toml
update_backend_version() {
    local new_version=$1

    if [ -f "backend/pyproject.toml" ]; then
        log_info "更新 backend/pyproject.toml"
        sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" backend/pyproject.toml
        rm backend/pyproject.toml.bak
        log_success "backend/pyproject.toml 已更新"
    fi
}

# 更新 frontend/package.json
update_frontend_version() {
    local new_version=$1

    if [ -f "frontend/package.json" ]; then
        log_info "更新 frontend/package.json"
        # 使用 node 来格式化 JSON（如果可用）
        if command -v node &> /dev/null; then
            node -e "
                const fs = require('fs');
                const pkg = JSON.parse(fs.readFileSync('frontend/package.json', 'utf8'));
                pkg.version = '$new_version';
                fs.writeFileSync('frontend/package.json', JSON.stringify(pkg, null, 2) + '\n');
            "
        else
            # 回退到 sed
            sed -i.bak "s/\"version\": \".*\"/\"version\": \"$new_version\"/" frontend/package.json
            rm frontend/package.json.bak
        fi
        log_success "frontend/package.json 已更新"
    fi
}

# 创建 git tag（可选）
create_git_tag() {
    local new_version=$1

    if [ -d ".git" ]; then
        log_info "创建 git tag: v$new_version"
        git add .
        git commit -m "chore: bump version to $new_version" || true
        git tag "v$new_version"
        log_success "Git tag v$new_version 已创建"
    fi
}

# 显示帮助信息
show_help() {
    cat << EOF
EmbedAI Agent 版本管理脚本

用法:
    $0 [increment_type] [options]

参数:
    increment_type    版本递增类型 (默认: patch)
                     - major: 主版本递增 (1.0.0 -> 2.0.0)
                     - minor: 次版本递增 (1.0.0 -> 1.1.0)
                     - patch: 补丁版本递增 (1.0.0 -> 1.0.1)

选项:
    -h, --help        显示此帮助信息
    --no-git-tag      不创建 git tag
    --dry-run         仅显示将要执行的操作，不实际修改文件

示例:
    $0                    # 补丁版本递增 (1.0.0 -> 1.0.1)
    $0 minor             # 次版本递增 (1.0.0 -> 1.1.0)
    $0 major             # 主版本递增 (1.0.0 -> 2.0.0)
    $0 --dry-run        # 预览模式
    $0 patch --no-git-tag # 递增版本但不创建 git tag

EOF
}

# 主函数
main() {
    local increment_type="patch"
    local create_tag=true
    local dry_run=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --no-git-tag)
                create_tag=false
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            major|minor|patch)
                increment_type=$1
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 检查是否在项目根目录
    if [ ! -f "CHANGELOG.md" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi

    # 获取当前版本
    local current_version=$(get_current_version)
    if [ -z "$current_version" ]; then
        log_error "无法读取当前版本号"
        exit 1
    fi

    # 计算新版本
    local new_version=$(increment_version "$current_version" "$increment_type")

    log_info "当前版本: $current_version"
    log_info "新版本: $new_version"
    log_info "递增类型: $increment_type"

    if [ "$dry_run" = true ]; then
        log_warning "预览模式 - 不会实际修改文件"
        echo
        echo "将要执行的操作:"
        echo "  - 更新 backend/pyproject.toml: $current_version -> $new_version"
        echo "  - 更新 frontend/package.json: $current_version -> $new_version"
        if [ "$create_tag" = true ]; then
            echo "  - 创建 git tag: v$new_version"
        fi
        exit 0
    fi

    # 更新版本文件
    update_backend_version "$new_version"
    update_frontend_version "$new_version"

    # 创建 git tag
    if [ "$create_tag" = true ]; then
        create_git_tag "$new_version"
    fi

    log_success "版本更新完成: $current_version -> $new_version"
    log_info "请记得更新 CHANGELOG.md 中的版本记录"
}

# 执行主函数
main "$@"
