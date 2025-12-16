#!/bin/bash

# Minimal version script
set -e

echo "[INFO] Starting version script..."

# Get current version
get_version() {
    if [ -f "backend/pyproject.toml" ]; then
        grep '^version = ' backend/pyproject.toml | sed 's/version = "\(.*\)"/\1/'
    else
        echo "[ERROR] Version file not found"
        exit 1
    fi
}

# Show help
show_help() {
    echo "EmbedAI Agent version management script"
    echo ""
    echo "Usage:"
    echo "    \$0 [increment_type] [options]"
    echo ""
    echo "Parameters:"
    echo "    increment_type    Version increment type (default: patch)"
    echo "                     - major: Major version increment (1.0.0 -> 2.0.0)"
    echo "                     - minor: Minor version increment (1.0.0 -> 1.1.0)"
    echo "                     - patch: Patch version increment (1.0.0 -> 1.0.1)"
    echo ""
    echo "Options:"
    echo "    -h, --help        Show this help message"
    echo "    --dry-run         Only show what would be done"
    echo ""
    echo "Examples:"
    echo "    \$0                # Patch version increment"
    echo "    \$0 --dry-run      # Preview mode"
}

# Main function
main() {
    local increment_type="patch"
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
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
                echo "[ERROR] Unknown parameter: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [ ! -f "CHANGELOG.md" ]; then
        echo "[ERROR] Please run from project root"
        exit 1
    fi

    local current_version=$(get_version)
    if [ -z "$current_version" ]; then
        echo "[ERROR] Unable to read version"
        exit 1
    fi

    echo "[INFO] Current version: $current_version"
    echo "[INFO] Increment type: $increment_type"

    if [ "$dry_run" = true ]; then
        echo "[WARNING] Preview mode - no changes will be made"
        echo "Would update to new version"
        exit 0
    fi

    echo "[SUCCESS] Script completed"
}

main "$@"
