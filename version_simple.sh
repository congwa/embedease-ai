#!/bin/bash

# Simple version script for testing
set -e

echo "Starting version script..."

# Get current version
get_version() {
    if [ -f "backend/pyproject.toml" ]; then
        grep '^version = ' backend/pyproject.toml | sed 's/version = "\(.*\)"/\1/'
    else
        echo "Error: version file not found"
        exit 1
    fi
}

# Main function
main() {
    echo "Current version: $(get_version)"
    echo "Script working!"
}

main "$@"
