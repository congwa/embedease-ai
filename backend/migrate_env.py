"""环境变量迁移脚本

自动将旧的 SILICONFLOW_* 配置迁移到新的通用配置格式

使用方法：
    python migrate_env.py

功能：
1. 自动备份原文件（.backup 后缀）
2. 将 SILICONFLOW_* 变量重命名为通用变量
3. 添加新的 LLM_PROVIDER 配置
4. 保持其他配置不变
"""

import re
import sys
from pathlib import Path


def migrate_env_file(env_path: str = ".env") -> bool:
    """迁移 .env 文件

    Args:
        env_path: .env 文件路径

    Returns:
        bool: 迁移是否成功
    """
    env_file = Path(env_path)

    if not env_file.exists():
        print(f"❌ 文件不存在: {env_path}")
        return False

    print(f"📄 开始迁移: {env_path}")

    # 读取原文件
    with open(env_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否已经迁移过
    if "LLM_PROVIDER" in content and "SILICONFLOW_API_KEY" not in content:
        print(f"✅ {env_path} 已经是新格式，无需迁移")
        return True

    # 备份
    backup_path = env_file.with_suffix(env_file.suffix + ".backup")
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 已备份到: {backup_path}")

    # 替换规则
    replacements = [
        (r"SILICONFLOW_API_KEY", "LLM_API_KEY"),
        (r"SILICONFLOW_BASE_URL", "LLM_BASE_URL"),
        (r"SILICONFLOW_CHAT_MODEL", "LLM_CHAT_MODEL"),
        (r"SILICONFLOW_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
        (r"SILICONFLOW_EMBEDDING_DIMENSION", "EMBEDDING_DIMENSION"),
        (r"SILICONFLOW_RERANK_ENABLED", "RERANK_ENABLED"),
        (r"SILICONFLOW_RERANK_MODEL", "RERANK_MODEL"),
        (r"SILICONFLOW_RERANK_TOP_N", "RERANK_TOP_N"),
        (r"SILICONFLOW_RERANK_INSTRUCTION", "RERANK_INSTRUCTION"),
        (r"SILICONFLOW_MODEL_PROFILES_JSON", "MODEL_PROFILES_JSON"),
    ]

    new_content = content
    changes_made = []

    for old, new in replacements:
        if old in new_content:
            new_content = re.sub(old, new, new_content)
            changes_made.append(f"  • {old} → {new}")

    # 添加新配置项
    if "LLM_PROVIDER" not in new_content:
        # 在文件开头添加 LLM_PROVIDER
        lines = new_content.split("\n")
        # 找到第一个非注释、非空行的位置
        insert_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                insert_pos = i
                break

        lines.insert(insert_pos, "LLM_PROVIDER=siliconflow")
        new_content = "\n".join(lines)
        changes_made.append("  • 添加 LLM_PROVIDER=siliconflow")

    # 添加新的可选配置项（如果不存在）
    optional_configs = [
        ("EMBEDDING_PROVIDER", "siliconflow"),
        ("RERANK_PROVIDER", None),
        ("EMBEDDING_API_KEY", None),
        ("EMBEDDING_BASE_URL", None),
        ("RERANK_API_KEY", None),
        ("RERANK_BASE_URL", None),
    ]

    for config_key, default_value in optional_configs:
        if config_key not in new_content:
            # 添加注释说明
            if default_value:
                new_content += f"\n{config_key}={default_value}"
            else:
                new_content += f"\n# {config_key}="

    # 更新 MODELS_DEV_PROVIDER_ID 的注释
    if "MODELS_DEV_PROVIDER_ID" in new_content:
        new_content = re.sub(
            r"MODELS_DEV_PROVIDER_ID=siliconflow",
            "# MODELS_DEV_PROVIDER_ID=siliconflow  # 默认使用 LLM_PROVIDER",
            new_content,
        )

    # 写入新文件
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ 迁移完成: {env_path}")
    if changes_made:
        print("📝 变更内容：")
        for change in changes_made:
            print(change)

    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🔄 环境变量迁移工具")
    print("=" * 60)
    print()

    # 迁移 .env 文件
    env_files = [".env", "../.env", "backend/.env"]
    migrated = False

    for env_file in env_files:
        if Path(env_file).exists():
            if migrate_env_file(env_file):
                migrated = True
            print()

    if not migrated:
        print("⚠️  未找到 .env 文件")
        print("请确保在项目根目录或 backend 目录下运行此脚本")
        return 1

    print("=" * 60)
    print("✨ 迁移完成！")
    print("=" * 60)
    print()
    print("📋 后续步骤：")
    print("1. 检查新的配置文件，确保所有值正确")
    print("2. 如需使用其他提供商，修改 LLM_PROVIDER 的值")
    print("3. 如果迁移有问题，可以从 .backup 文件恢复")
    print("4. 重启应用以使用新配置")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

