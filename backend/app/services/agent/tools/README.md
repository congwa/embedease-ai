](#工具选择建议)
- [开发指南](#开发指南)

---

## 工具概览

| 工具名称 | 功能 | 适用场景 | 输入 | 输出 |
|---------|------|---------|------|------|
| **search_products** | 搜索商品 | 用户表达购物需求 | 查询字符串 | 商品列表(JSON) |
| **get_product_details** | 获取商品详情 | 查看具体商品信息 | 商品ID | 商品详情(JSON) |
| **compare_products** | 对比商品 | 多选一决策 | 商品ID列表 | 对比结果(JSON) |
| **filter_by_price** | 价格过滤 | 预算限制搜索 | 价格区间 | 商品列表(JSON) |

---

## 工具详解

### 1. search_products

**文件**: `search_products.py`

#### 功能描述
根据用户的自然语言需求描述，搜索匹配的商品。使用增强检索策略（向量相似度 + 关键词过滤 + 相关性重排序）。

#### 输入参数
```python
query: str  # 用户的搜索需求描述
```

#### 输出格式
```json
[
  {
    "id": "P001",
    "name": "索尼 WH-1000XM5 无线降噪耳机",
    "price": 2999.0,
    "summary": "索尼 WH-1000XM5 是索尼最新一代旗舰降噪耳机...",
    "url": "http://localhost:3000/products/P001",
    "category": "电子产品/耳机"
  }
]
```

#### 使用示例
```python
# 示例 1: 品类搜索
search_products("降噪耳机")

# 示例 2: 特性搜索
search_products("适合学生的笔记本电脑")

# 示例 3: 场景搜索
search_products("跑步用的运动鞋")
```

#### 检索策略
1. **向量相似度检索**：基于语义理解匹配商品
2. **关键词提取与过滤**：提取查询中的关键词，过滤更相关的结果
3. **相关性重排序**：综合考虑关键词匹配度、价格合理性、内容丰富度

#### 配置选项
```python
USE_ENHANCED_RETRIEVAL = True  # 是否启用增强检索
```

---

### 2. get_product_details

**文件**: `get_product_details.py`

#### 功能描述
根据商品ID获取指定商品的详细信息，包括完整描述、规格参数等。

#### 输入参数
```python
product_id: str  # 商品ID，如 "P001"
```

#### 输出格式
```json
{
  "id": "P001",
  "name": "索尼 WH-1000XM5 无线降噪耳机",
  "price": 2999.0,
  "category": "电子产品/耳机",
  "description": "索尼 WH-1000XM5 是索尼最新一代旗舰降噪耳机。采用全新设计的 8 个麦克风系统...",
  "url": "http://localhost:3000/products/P001"
}
```

#### 使用示例
```python
# 获取某个商品的详细信息
get_product_details("P001")

# 配合 search_products 使用
# 1. 先搜索商品
results = search_products("降噪耳机")
# 2. 提取商品ID
product_id = results[0]["id"]
# 3. 获取详情
details = get_product_details(product_id)
```

#### 与 search_products 的区别
- `search_products`: 模糊搜索，根据需求描述查找
- `get_product_details`: 精确查询，根据ID获取完整信息

---

### 3. compare_products

**文件**: `compare_products.py`

#### 功能描述
对比多个商品的差异，包括价格、分类、特性等，帮助用户做出购买决策。

#### 输入参数
```python
product_ids: list[str]  # 商品ID列表，至少2个
```

#### 输出格式
```json
{
  "products": [
    {
      "id": "P001",
      "name": "索尼 WH-1000XM5",
      "price": 2999.0,
      "category": "电子产品/耳机",
      "description": "索尼 WH-1000XM5 是索尼最新一代...",
      "url": "http://localhost:3000/products/P001"
    },
    {
      "id": "P002",
      "name": "苹果 AirPods Pro 2",
      "price": 1899.0,
      "category": "电子产品/耳机",
      "description": "Apple AirPods Pro 2 配备全新 H2 芯片...",
      "url": "http://localhost:3000/products/P002"
    }
  ],
  "comparison_points": {
    "price_range": {
      "lowest": 1899.0,
      "highest": 2999.0,
      "average": 2449.0
    },
    "categories": ["电子产品/耳机"],
    "product_count": 2
  }
}
```

#### 使用示例
```python
# 示例 1: 对比两款耳机
compare_products(["P001", "P002"])

# 示例 2: 对比三款笔记本
compare_products(["P006", "P007", "P008"])

# 示例 3: 完整工作流
# 1. 搜索商品
results = search_products("降噪耳机")
# 2. 提取前3个商品的ID
product_ids = [p["id"] for p in results[:3]]
# 3. 对比这些商品
comparison = compare_products(product_ids)
```

#### 对比维度
- **价格对比**：最低价、最高价、平均价
- **分类信息**：商品所属类别
- **描述对比**：各商品的特点和描述
- **统计信息**：商品数量等

---

### 4. filter_by_price

**文件**: `filter_by_price.py`

#### 功能描述
根据价格区间过滤商品，帮助用户在预算内找到合适的商品。

#### 输入参数
```python
min_price: float | None = None  # 最低价格（元）
max_price: float | None = None  # 最高价格（元）
```

#### 输出格式
```json
[
  {
    "id": "P004",
    "name": "Nike Air Zoom Pegasus 40",
    "price": 899.0,
    "summary": "Nike Pegasus 40 是经典跑鞋系列的最新款...",
    "url": "http://localhost:3000/products/P004",
    "category": "运动/跑步鞋"
  }
]
```

#### 使用示例
```python
# 示例 1: 查找 1000-2000 元的商品
filter_by_price(min_price=1000, max_price=2000)

# 示例 2: 查找 3000 元以下的商品
filter_by_price(max_price=3000)

# 示例 3: 查找 2000 元以上的高端商品
filter_by_price(min_price=2000)

# 示例 4: 不限制价格（不推荐，会返回所有商品）
filter_by_price()
```

#### 价格过滤逻辑
- 只传 `min_price`：查找该价格以上的商品
- 只传 `max_price`：查找该价格以下的商品
- 同时传入：查找价格区间内的商品
- 都不传：返回所有商品（不推荐）

---

## 工具组合使用

### 场景 1: 预算内推荐

```python
# 用户需求："推荐2000元以下的降噪耳机"

# 方案A：先过滤价格，再分析需求
products = filter_by_price(max_price=2000)
# 然后在结果中根据"降噪"特性筛选

# 方案B：先搜索需求，再过滤价格
products = search_products("降噪耳机")
# 然后从结果中筛选 price <= 2000 的商品
```

### 场景 2: 对比分析

```python
# 用户需求："对比一下这几款耳机，哪个更适合我"

# 步骤1：搜索商品
results = search_products("降噪耳机")

# 步骤2：提取前3个商品ID
product_ids = [p["id"] for p in results[:3]]

# 步骤3：对比商品
comparison = compare_products(product_ids)

# 步骤4：分析对比结果并给出建议
# 基于 comparison["comparison_points"] 生成建议
```

### 场景 3: 详细了解

```python
# 用户需求："这款商品怎么样？"

# 步骤1：搜索定位商品
results = search_products("索尼降噪耳机")

# 步骤2：获取第一个结果的详情
product_id = results[0]["id"]
details = get_product_details(product_id)

# 步骤3：基于详细信息给出评价
```

---

## 工具选择建议

### 决策树

```
用户输入
    │
    ├─ 有明确价格预算？
    │   └─ YES → filter_by_price + search_products
    │   └─ NO  ↓
    │
    ├─ 想要对比多个商品？
    │   └─ YES → search_products → compare_products
    │   └─ NO  ↓
    │
    ├─ 询问具体商品信息？
    │   └─ YES → get_product_details
    │   └─ NO  ↓
    │
    └─ 一般性搜索需求
        └─ search_products
```

### 最佳实践

1. **搜索优先**：大多数场景从 `search_products` 开始
2. **价格敏感**：有预算限制时使用 `filter_by_price`
3. **深入了解**：需要详细信息时使用 `get_product_details`
4. **对比决策**：多选一时使用 `compare_products`

---

## 开发指南

### 添加新工具

1. 在 `tools/` 目录下创建新文件 `your_tool.py`
2. 定义 Pydantic 模型（输入输出）
3. 使用 `@tool` 装饰器定义工具函数
4. 添加详细的文档字符串
5. 在 `__init__.py` 中导出
6. 更新本 README

### 工具开发规范

```python
"""工具名称

## 功能描述
简要描述工具的功能

## 使用场景
列出适用的场景

## 输出格式
说明返回的数据结构
"""

from langchain.tools import tool
from pydantic import BaseModel, Field

class YourToolResponse(BaseModel):
    """返回结果模型"""
    field1: str = Field(description="字段1说明")
    field2: int = Field(description="字段2说明")

@tool
def your_tool(param: str) -> str:
    """工具的简短描述

    详细说明工具的功能、参数、返回值等。

    Args:
        param: 参数说明

    Returns:
        返回值说明

    Examples:
        >>> your_tool("example")
        '{"result": "..."}'
    """
    # 实现逻辑
    pass
```

### 测试工具

```python
# 单元测试示例
def test_search_products():
    result = search_products("测试查询")
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, list)
```

---

## 常见问题

### Q1: 工具返回的是什么格式？
A: 所有工具都返回 JSON 字符串，可以用 `json.loads()` 解析为 Python 对象。

### Q2: 如何启用/禁用增强检索？
A: 在 `__init__.py` 中设置 `USE_ENHANCED_RETRIEVAL = True/False`。

### Q3: 工具调用失败怎么办？
A: 所有工具都有异常处理，会返回包含 `error` 字段的 JSON。

### Q4: 如何添加日志？
A: 每个工具文件都有自己的 logger，使用 `logger.info/debug/error` 记录。

---

## 更新日志

### v1.0.0 (2024-12-16)
- ✨ 初始版本
- ✅ 实现 4 个核心工具
- ✅ 添加结构化输出模型
- ✅ 完善文档和示例
- ✅ 实现增强检索策略

