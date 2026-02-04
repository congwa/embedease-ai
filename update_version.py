#!/usr/bin/env python3
"""
Simple version update script for EmbedEase AI
# 预览模式
python3 update_version.py --dry-run

# 补丁版本更新 (默认)
python3 update_version.py

# 次版本更新
python3 update_version.py minor

# 主版本更新  
python3 update_version.py major

# 查看帮助
python3 update_version.py --help

# 检查版本一致性（用于 CI/打 tag 前）
python3 update_version.py --check
"""

import re
import sys
import json
from pathlib import Path

# SDK 包配置
SDK_PACKAGES = [
    {
        "name": "@embedease/chat-sdk",
        "path": "frontend/packages/chat-sdk/package.json",
        "type": "npm",
    },
    {
        "name": "@embedease/chat-sdk-react",
        "path": "frontend/packages/chat-sdk-react/package.json",
        "type": "npm",
    },
    {
        "name": "langgraph-agent-kit",
        "path": "backend/packages/langgraph-agent-kit/pyproject.toml",
        "type": "pyproject",
    },
]


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


def get_package_version(pkg_config):
    """Get version from a package config"""
    path = Path(pkg_config["path"])
    if not path.exists():
        return None

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if pkg_config["type"] == "npm":
        pkg = json.loads(content)
        return pkg.get("version")
    elif pkg_config["type"] == "pyproject":
        match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
        return match.group(1) if match else None

    return None

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


def update_sdk_package_version(pkg_config, new_version):
    """Update SDK package version"""
    path = Path(pkg_config["path"])
    if not path.exists():
        print(f"⚠️  {pkg_config['path']} not found, skipping")
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if pkg_config["type"] == "npm":
        pkg = json.loads(content)
        pkg['version'] = new_version
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(pkg, f, indent=2, ensure_ascii=False)
            f.write('\n')
    elif pkg_config["type"] == "pyproject":
        content = re.sub(
            r'^version = "[^"]*"',
            f'version = "{new_version}"',
            content,
            flags=re.MULTILINE
        )
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"✅ Updated {pkg_config['name']}: {new_version}")
    return True


def update_all_sdk_packages(new_version):
    """Update all SDK packages"""
    print("\n📦 Updating SDK packages...")
    for pkg in SDK_PACKAGES:
        update_sdk_package_version(pkg, new_version)


def check_version_consistency():
    """Check if all versions are consistent"""
    print("\n🔍 Checking version consistency...")
    
    main_version = get_current_version()
    print(f"📦 Main version (backend/pyproject.toml): {main_version}")
    
    # Check frontend
    frontend_path = Path("frontend/package.json")
    if frontend_path.exists():
        with open(frontend_path, 'r', encoding='utf-8') as f:
            frontend_version = json.load(f).get("version")
        print(f"📦 Frontend version: {frontend_version}")
    else:
        frontend_version = None
        print("⚠️  Frontend package.json not found")
    
    # Check SDK packages
    sdk_versions = {}
    for pkg in SDK_PACKAGES:
        version = get_package_version(pkg)
        sdk_versions[pkg["name"]] = version
        status = "✅" if version == main_version else "❌"
        print(f"{status} {pkg['name']}: {version or 'not found'}")
    
    # Determine consistency
    all_versions = [main_version]
    if frontend_version:
        all_versions.append(frontend_version)
    all_versions.extend([v for v in sdk_versions.values() if v])
    
    is_consistent = len(set(all_versions)) == 1
    
    if is_consistent:
        print(f"\n✅ All versions are consistent: {main_version}")
        return True, main_version
    else:
        print(f"\n❌ Version mismatch detected!")
        print(f"   Expected: {main_version}")
        return False, main_version

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("EmbedEase AI Version Update Script")
        print("")
        print("Usage:")
        print("    python update_version.py [increment_type] [options]")
        print("")
        print("Parameters:")
        print("    increment_type    Version increment type (default: patch)")
        print("                     - major: Major version increment")
        print("                     - minor: Minor version increment")
        print("                     - patch: Patch version increment")
        print("")
        print("Options:")
        print("    --dry-run         Only show what would be done")
        print("    --check           Check version consistency (for CI/pre-tag)")
        print("    --no-sdk          Skip SDK packages update")
        print("")
        print("Examples:")
        print("    python update_version.py              # Patch update all")
        print("    python update_version.py minor        # Minor update all")
        print("    python update_version.py --check      # Check consistency")
        print("    python update_version.py --dry-run    # Preview changes")
        print("")
        return

    increment_type = "patch"
    dry_run = False
    check_only = False
    update_sdk = True

    for arg in sys.argv[1:]:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--check":
            check_only = True
        elif arg == "--no-sdk":
            update_sdk = False
        elif arg in ["major", "minor", "patch"]:
            increment_type = arg

    try:
        # Check mode
        if check_only:
            is_consistent, _ = check_version_consistency()
            sys.exit(0 if is_consistent else 1)

        current_version = get_current_version()
        new_version = increment_version(current_version, increment_type)

        print(f"📦 Current version: {current_version}")
        print(f"🎯 New version: {new_version}")
        print(f"🔧 Increment type: {increment_type}")

        if dry_run:
            print("\n🔍 Preview mode - no changes will be made")
            print("\nWould update:")
            print(f"  - backend/pyproject.toml")
            print(f"  - frontend/package.json")
            if update_sdk:
                for pkg in SDK_PACKAGES:
                    print(f"  - {pkg['path']}")
            return

        update_backend_version(new_version)
        update_frontend_version(new_version)

        if update_sdk:
            update_all_sdk_packages(new_version)

        print(f"\n🎉 Version update completed: {current_version} -> {new_version}")
        print("💡 Remember to update CHANGELOG.md and commit changes")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
