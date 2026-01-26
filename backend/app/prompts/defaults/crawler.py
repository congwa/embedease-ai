"""爬虫提取提示词默认值"""

CRAWLER_PROMPTS: dict[str, dict] = {
    "crawler.product_extraction": {
        "category": "crawler",
        "name": "商品信息提取",
        "description": "从网页 HTML 中提取商品信息",
        "variables": ["html_content"],
        "content": """你是一个专业的网页商品信息提取助手。请分析以下 HTML 内容，判断是否为商品详情页，如果是则提取商品信息。

## 判断标准
商品详情页通常包含：
- 商品名称/标题
- 价格信息
- 商品描述或规格
- 购买相关元素（加购、立即购买等）

## 提取字段
如果是商品详情页，请提取以下信息：
- name: 商品名称
- price: 价格（数字，不含货币符号）
- original_price: 原价（如有）
- description: 商品描述
- category: 商品类别
- brand: 品牌
- specifications: 规格参数（JSON 对象）
- images: 图片链接列表
- stock_status: 库存状态
- rating: 评分
- review_count: 评价数量

## 输出格式
请以 JSON 格式返回：
```json
{{
    "is_product_page": true/false,
    "confidence": 0.0-1.0,
    "reason": "判断理由",
    "product": {{
        "name": "...",
        "price": 0.0,
        ...
    }}
}}
```

如果不是商品页，product 字段为 null。

## HTML 内容
{html_content}
""",
    },
    "crawler.content_extraction": {
        "category": "crawler",
        "name": "通用内容提取",
        "description": "从网页中提取主要文本内容",
        "variables": ["html_content"],
        "content": """你是一个专业的网页内容提取助手。请从以下 HTML 中提取主要文本内容。

## 提取规则
1. 提取页面主体内容，忽略导航、页脚、广告等
2. 保持文本的逻辑结构
3. 提取标题、正文、列表等核心内容
4. 清理 HTML 标签，只保留纯文本

## 输出格式
```json
{{
    "title": "页面标题",
    "content": "主体内容文本",
    "summary": "内容摘要（100字以内）",
    "keywords": ["关键词1", "关键词2"]
}}
```

## HTML 内容
{html_content}
""",
    },
}
