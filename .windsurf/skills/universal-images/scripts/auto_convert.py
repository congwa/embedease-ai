#!/usr/bin/env python3
"""
通用图片路径转换脚本
支持GitHub和Gitee双平台的图片引用处理
"""

import os
import re
import subprocess
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

class UniversalImageConverter:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.github_raw_base = None
        self.gitee_raw_base = None
        
    def detect_git_remotes(self) -> Tuple[Optional[str], Optional[str]]:
        """检测GitHub和Gitee远程仓库地址"""
        try:
            result = subprocess.run(
                ["git", "remote", "-v"], 
                capture_output=True, 
                text=True, 
                cwd=self.repo_path
            )
            github_url = None
            gitee_url = None
            
            for line in result.stdout.split('\n'):
                if 'github.com' in line and 'fetch' in line:
                    github_url = line.split()[1]
                elif 'gitee.com' in line and 'fetch' in line:
                    gitee_url = line.split()[1]
            
            # 转换为raw URL
            if github_url:
                # git@github.com:user/repo.git -> https://raw.githubusercontent.com/user/repo/main/
                if github_url.startswith('git@'):
                    github_url = github_url.replace('git@github.com:', 'https://github.com/')
                if github_url.endswith('.git'):
                    github_url = github_url[:-4]
                if github_url.startswith('https://github.com/'):
                    self.github_raw_base = github_url.replace('https://github.com/', 'https://raw.githubusercontent.com/') + '/main/'
                    
            if gitee_url:
                # git@gitee.com:user/repo.git -> https://gitee.com/user/repo/raw/
                if gitee_url.startswith('git@'):
                    gitee_url = gitee_url.replace('git@gitee.com:', 'https://gitee.com/')
                if gitee_url.endswith('.git'):
                    gitee_url = gitee_url[:-4]
                if gitee_url.startswith('https://gitee.com/'):
                    self.gitee_raw_base = gitee_url + '/raw/'
                    
            return self.github_raw_base, self.gitee_raw_base
            
        except Exception as e:
            print(f"检测Git远程仓库失败: {e}")
            return None, None
    
    def find_readme_files(self) -> List[Path]:
        """查找所有README文件"""
        readme_files = []
        for readme in self.repo_path.glob("**/README*.md"):
            # 跳过node_modules和其他忽略的目录
            if any(ignored in str(readme) for ignored in ['node_modules', '.git', 'dist', 'build']):
                continue
            readme_files.append(readme)
        return readme_files
    
    def extract_image_references(self, content: str) -> List[Tuple[str, str]]:
        """提取图片引用，返回(原始引用, 图片路径)"""
        # 匹配 ![alt](path) 格式
        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        images = []
        
        for match in re.finditer(pattern, content):
            alt_text, path = match.groups()
            # 处理所有图片引用，除了badge等外部服务
            if not any(service in path for service in ['img.shields.io', 'github.com/LuanRoger', 'github.com/actions']):
                images.append((match.group(0), path))
        
        return images
    
    def convert_to_jsdelivr_cdn(self, image_path: str) -> str:
        """转换为jsdelivr CDN URL"""
        if not self.github_raw_base:
            return image_path
        
        # 如果已经是GitHub Raw URL，转换为jsdelivr CDN
        if 'raw.githubusercontent.com' in image_path:
            # https://raw.githubusercontent.com/user/repo/main/path -> https://cdn.jsdelivr.net/gh/user/repo@main/path
            return image_path.replace('https://raw.githubusercontent.com/', 'https://cdn.jsdelivr.net/gh/').replace('/main/', '@main/')
        
        # 如果是相对路径，转换为jsdelivr CDN
        clean_path = image_path.lstrip('./')
        repo_part = self.github_raw_base.replace('https://raw.githubusercontent.com/', '').replace('/main/', '')
        return f"https://cdn.jsdelivr.net/gh/{repo_part}@main/{clean_path}"
    
    def convert_to_gitee_raw(self, image_path: str) -> str:
        """转换为Gitee Raw URL"""
        if not self.gitee_raw_base:
            return image_path
        
        clean_path = image_path.lstrip('./')
        return f"{self.gitee_raw_base}{clean_path}"
    
    def convert_to_github_raw(self, image_path: str) -> str:
        """转换为GitHub Raw URL"""
        if not self.github_raw_base:
            return image_path
        
        # 移除开头的 ./
        clean_path = image_path.lstrip('./')
        return f"{self.github_raw_base}{clean_path}"
    
    def convert_to_relative(self, image_path: str) -> str:
        """转换为相对路径"""
        # 如果是GitHub Raw URL，提取相对路径
        if 'raw.githubusercontent.com' in image_path:
            # https://raw.githubusercontent.com/user/repo/main/path -> path
            parts = image_path.split('/main/')
            if len(parts) > 1:
                return parts[1]
        
        # 如果是jsdelivr CDN URL，提取相对路径
        if 'cdn.jsdelivr.net/gh' in image_path:
            # https://cdn.jsdelivr.net/gh/user/repo@main/path -> path
            parts = image_path.split('@main/')
            if len(parts) > 1:
                return parts[1]
        
        # 如果是其他外部URL，提取文件名
        if image_path.startswith(('http://', 'https://')):
            filename = image_path.split('/')[-1]
            return filename
        
        return image_path
    
    def process_file(self, file_path: Path, platform: str, dry_run: bool = False) -> bool:
        """处理单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            images = self.extract_image_references(content)
            
            if not images:
                print(f"  无本地图片引用")
                return False
            
            print(f"  发现 {len(images)} 个图片引用:")
            
            for full_match, image_path in images:
                old_path = image_path
                new_path = None
                
                if platform == "jsdelivr-cdn":
                    new_path = self.convert_to_jsdelivr_cdn(image_path)
                elif platform == "github-raw":
                    new_path = self.convert_to_github_raw(image_path)
                elif platform == "gitee-raw":
                    new_path = self.convert_to_gitee_raw(image_path)
                elif platform == "relative":
                    new_path = self.convert_to_relative(image_path)
                elif platform == "universal":
                    # 优先使用jsdelivr CDN
                    new_path = self.convert_to_jsdelivr_cdn(image_path)
                
                if new_path and new_path != image_path:
                    print(f"    {image_path} -> {new_path}")
                    content = content.replace(full_match, full_match.replace(image_path, new_path))
            
            if content != original_content:
                if dry_run:
                    print(f"  [预览] 将修改 {len(images)} 个图片引用")
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  已修改 {len(images)} 个图片引用")
                return True
            else:
                print(f"  无需修改")
                return False
                
        except Exception as e:
            print(f"  处理文件失败: {e}")
            return False
    
    def convert_all(self, platform: str = "universal", dry_run: bool = False) -> None:
        """转换所有README文件"""
        print(f"检测Git远程仓库...")
        github_url, gitee_url = self.detect_git_remotes()
        
        if github_url:
            print(f"GitHub: {github_url}")
        if gitee_url:
            print(f"Gitee: {gitee_url}")
        
        readme_files = self.find_readme_files()
        print(f"找到 {len(readme_files)} 个README文件")
        
        modified_count = 0
        for readme_file in readme_files:
            print(f"\n处理: {readme_file.relative_to(self.repo_path)}")
            if self.process_file(readme_file, platform, dry_run):
                modified_count += 1
        
        if dry_run:
            print(f"\n预览完成: {modified_count} 个文件将被修改")
        else:
            print(f"\n转换完成: 修改了 {modified_count} 个文件")

def main():
    parser = argparse.ArgumentParser(description="通用图片路径转换工具")
    parser.add_argument("--platform", choices=["jsdelivr-cdn", "github-raw", "gitee-raw", "relative", "universal"], 
                       default="universal", help="目标平台格式")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不修改文件")
    parser.add_argument("--path", default=".", help="仓库路径")
    
    args = parser.parse_args()
    
    converter = UniversalImageConverter(args.path)
    converter.convert_all(args.platform, args.dry_run)

if __name__ == "__main__":
    main()
