#!/bin/bash

# EmbedAI Agent version management script
# Auto increment version and update related files

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
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

# Get current version
get_current_version() {
    if [ -f "backend/pyproject.toml" ]; then
        grep '^version = ' backend/pyproject.toml | sed 's/version = "\(.*\)"/\1/'
    elif [ -f "pyproject.toml" ]; then
        grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
    else
        log_error "Version file not found (pyproject.toml)"
        exit 1
    fi
}

# Increment version
increment_version() {
    local version=$1
    local increment_type=${2:-"patch"}

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
            log_error "Invalid increment type: $increment_type (supported: major, minor, patch)"
            exit 1
            ;;
    esac

    echo "$major.$minor.$patch"
}

# Update backend/pyproject.toml
update_backend_version() {
    local new_version=$1

    if [ -f "backend/pyproject.toml" ]; then
        log_info "Updating backend/pyproject.toml"
        sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" backend/pyproject.toml
        rm backend/pyproject.toml.bak
        log_success "backend/pyproject.toml updated"
    fi
}

# Update frontend/package.json
update_frontend_version() {
    local new_version=$1

    if [ -f "frontend/package.json" ]; then
        log_info "Updating frontend/package.json"
        if command -v node &> /dev/null; then
            node -e "
                const fs = require('fs');
                const pkg = JSON.parse(fs.readFileSync('frontend/package.json', 'utf8'));
                pkg.version = '$new_version';
                fs.writeFileSync('frontend/package.json', JSON.stringify(pkg, null, 2) + '\n');
            "
        else
            sed -i.bak "s/\"version\": \".*\"/\"version\": \"$new_version\"/" frontend/package.json
            rm frontend/package.json.bak
        fi
        log_success "frontend/package.json updated"
    fi
}

# Create git tag (optional)
create_git_tag() {
    local new_version=$1

    if [ -d ".git" ]; then
        log_info "Creating git tag: v$new_version"
        git add .
        git commit -m "chore: bump version to $new_version" || true
        git tag "v$new_version"
        log_success "Git tag v$new_version created"
    fi
}

# Show help
show_help() {
    cat << 'EOF'
EmbedAI Agent version management script

Usage:
    $0 [increment_type] [options]

Parameters:
    increment_type    Version increment type (default: patch)
                     - major: Major version increment (1.0.0 -> 2.0.0)
                     - minor: Minor version increment (1.0.0 -> 1.1.0)
                     - patch: Patch version increment (1.0.0 -> 1.0.1)

Options:
    -h, --help        Show this help message
    --no-git-tag      Do not create git tag
    --dry-run         Only show what would be done, do not modify files

Examples:
    $0                    # Patch version increment (1.0.0 -> 1.0.1)
    $0 minor             # Minor version increment (1.0.0 -> 1.1.0)
    $0 major             # Major version increment (1.0.0 -> 2.0.0)
    $0 --dry-run        # Preview mode
    $0 patch --no-git-tag # Increment version but do not create git tag

EOF
}

# Main function
main() {
    local increment_type="patch"
    local create_tag=true
    local dry_run=false

    # Parse command line arguments
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
                log_error "Unknown parameter: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Check if in project root
    if [ ! -f "CHANGELOG.md" ]; then
        log_error "Please run this script from the project root directory"
        exit 1
    fi

    # Get current version
    local current_version=$(get_current_version)
    if [ -z "$current_version" ]; then
        log_error "Unable to read current version"
        exit 1
    fi

    # Calculate new version
    local new_version=$(increment_version "$current_version" "$increment_type")

    log_info "Current version: $current_version"
    log_info "New version: $new_version"
    log_info "Increment type: $increment_type"

    if [ "$dry_run" = true ]; then
        log_warning "Preview mode - files will not be modified"
        echo
        echo "Operations to be performed:"
        echo "  - Update backend/pyproject.toml: $current_version -> $new_version"
        echo "  - Update frontend/package.json: $current_version -> $new_version"
        if [ "$create_tag" = true ]; then
            echo "  - Create git tag: v$new_version"
        fi
        exit 0
    fi

    # Update version files
    update_backend_version "$new_version"
    update_frontend_version "$new_version"

    # Create git tag
    if [ "$create_tag" = true ]; then
        create_git_tag "$new_version"
    fi

    log_success "Version update completed: $current_version -> $new_version"
    log_info "Remember to update CHANGELOG.md with version notes"
}

# Execute main function
main "$@"
