#!/usr/bin/env python3
"""
Simple version update script for EmbedAI Agent
"""

import re
import sys
import json
from pathlib import Path

def get_current_version():
    """Get current version from backend/pyproject.toml"""
    pyproject_path = Path("backend/pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("backend/pyproject.toml not found")

    with open(pyproject_path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Version not found in pyproject.toml")

    return match.group(1)

def increment_version(version, increment_type="patch"):
    """Increment version number"""
    major, minor, patch = map(int, version.split('.'))

    if increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid increment type: {increment_type}")

    return f"{major}.{minor}.{patch}"

def update_backend_version(new_version):
    """Update backend/pyproject.toml"""
    pyproject_path = Path("backend/pyproject.toml")

    with open(pyproject_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update version
    content = re.sub(
        r'^version = "[^"]*"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE
    )

    with open(pyproject_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Updated backend/pyproject.toml: {new_version}")

def update_frontend_version(new_version):
    """Update frontend/package.json"""
    package_path = Path("frontend/package.json")
    if not package_path.exists():
        print("⚠️  frontend/package.json not found, skipping")
        return

    with open(package_path, 'r', encoding='utf-8') as f:
        pkg = json.load(f)

    pkg['version'] = new_version

    with open(package_path, 'w', encoding='utf-8') as f:
        json.dump(pkg, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"✅ Updated frontend/package.json: {new_version}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("EmbedAI Agent Version Update Script")
        print("")
        print("Usage:")
        print("    python update_version.py [increment_type] [--dry-run]")
        print("")
        print("Parameters:")
        print("    increment_type    Version increment type (default: patch)")
        print("                     - major: Major version increment")
        print("                     - minor: Minor version increment")
        print("                     - patch: Patch version increment")
        print("")
        print("Options:")
        print("    --dry-run         Only show what would be done")
        print("")
        return

    increment_type = "patch"
    dry_run = False

    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg in ["major", "minor", "patch"]:
            increment_type = arg

    try:
        current_version = get_current_version()
        new_version = increment_version(current_version, increment_type)

        print(f"📦 Current version: {current_version}")
        print(f"🎯 New version: {new_version}")
        print(f"🔧 Increment type: {increment_type}")

        if dry_run:
            print("🔍 Preview mode - no changes will be made")
            return

        update_backend_version(new_version)
        update_frontend_version(new_version)

        print(f"🎉 Version update completed: {current_version} -> {new_version}")
        print("💡 Remember to update CHANGELOG.md and commit changes")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
