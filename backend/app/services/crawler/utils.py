"""爬虫工具函数"""

from urllib.parse import urlparse


def normalize_domain(url: str) -> str:
    """规范化域名
    
    从 URL 中提取域名并规范化，用于站点去重。
    
    规则：
    1. 提取 netloc（域名+端口）
    2. 转小写
    3. **保留完整域名**（包括所有子域名），不做任何删减
    
    设计说明：
    - 每个完整域名（含子域名）被视为独立站点
    - example.com、new.example.com、new2.example.com 是三个不同站点
    - www.example.com 也是独立站点（不会被转换为 example.com）
    - 这样可以支持同一主域名下的多个子站点独立爬取
    
    Args:
        url: 完整 URL
        
    Returns:
        规范化后的域名（小写，保留子域名和端口）
        
    Examples:
        >>> normalize_domain("https://www.example.com/path")
        'www.example.com'
        >>> normalize_domain("https://new.example.com/path")
        'new.example.com'
        >>> normalize_domain("https://new2.example.com/path")
        'new2.example.com'
        >>> normalize_domain("http://Example.COM:8080/")
        'example.com:8080'
    """
    parsed = urlparse(url)
    # 提取域名并转小写，保留完整域名（包括子域名和端口）
    domain = parsed.netloc.lower()

    return domain


def generate_site_id(domain: str) -> str:
    """根据域名生成站点 ID
    
    将域名转换为合法的站点 ID（替换特殊字符）。
    
    Args:
        domain: 规范化后的域名
        
    Returns:
        站点 ID
        
    Examples:
        >>> generate_site_id("example.com")
        'example_com'
        >>> generate_site_id("example.com:8080")
        'example_com_8080'
    """
    return domain.replace(".", "_").replace(":", "_")
