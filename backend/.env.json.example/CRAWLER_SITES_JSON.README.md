# CRAWLER_SITES_JSON.json 配置说明

## 文件作用

定义要爬取的网站及其爬取规则，用于自动化采集商品信息到系统中。

## 配置格式

```json
[
  {
    "id": "站点唯一标识",
    "name": "站点名称",
    "start_url": "起始URL",
    "status": "active|inactive",
    "link_pattern": "链接匹配正则",
    "max_depth": 3,
    "max_pages": 500,
    "crawl_delay": 1.0,
    "is_spa": true,
    "wait_for_selector": "body",
    "wait_timeout": 10000,
    "cron_expression": "0 2 * * *",
    "extraction_config": {
      "mode": "selector",
      "product_page_indicator": ".product-detail",
      "fields": { ... }
    }
  }
]
```

## 字段说明

### 基础配置

| 字段 | 类型 | 说明 | 必填 | 示例 |
|------|------|------|------|------|
| `id` | string | 站点唯一标识符 | ✅ | `"example_com"` |
| `name` | string | 站点显示名称 | ✅ | `"example官网"` |
| `start_url` | string | 爬取起始 URL | ✅ | `"https://example.com"` |
| `status` | string | 站点状态：`active`/`inactive` | ✅ | `"active"` |

### 爬取控制

| 字段 | 类型 | 说明 | 默认值 | 示例 |
|------|------|------|--------|------|
| `link_pattern` | string | 链接匹配正则表达式 | `null` | `"^https://example\\.com/.*"` |
| `max_depth` | number | 最大爬取深度 | `3` | `3` |
| `max_pages` | number | 最大爬取页面数 | `100` | `500` |
| `crawl_delay` | number | 爬取延迟（秒） | `1.0` | `1.0` |

### SPA 支持

| 字段 | 类型 | 说明 | 默认值 | 示例 |
|------|------|------|--------|------|
| `is_spa` | boolean | 是否为单页应用 | `false` | `true` |
| `wait_for_selector` | string | 等待的 CSS 选择器 | `null` | `"body"` |
| `wait_timeout` | number | 等待超时时间（毫秒） | `10000` | `10000` |

### 定时任务

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `cron_expression` | string | Cron 表达式（定时爬取） | `"0 2 * * *"` 每天凌晨2点 |

### 提取配置

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
| `extraction_config.mode` | string | 提取模式：`selector`/`llm` | ✅ |
| `extraction_config.product_page_indicator` | string | 商品页面识别选择器 | 否 |
| `extraction_config.fields` | object | 字段提取规则 | ✅ |

### 字段提取规则

每个字段支持以下配置：

```json
{
  "字段名": {
    "selector": "CSS选择器",
    "attribute": "属性名（默认为文本内容）",
    "multiple": true/false,
    "required": true/false
  }
}
```

## 完整示例

```json
[
  {
    "id": "example_com",
    "name": "example官网",
    "start_url": "https://www.example.com",
    "status": "active",
    "link_pattern": "^https://www\\.example\\.com/.*",
    "max_depth": 3,
    "max_pages": 500,
    "crawl_delay": 1.0,
    "is_spa": true,
    "wait_for_selector": "body",
    "wait_timeout": 10000,
    "cron_expression": "0 2 * * *",
    "extraction_config": {
      "mode": "selector",
      "product_page_indicator": ".product-detail",
      "fields": {
        "name": {
          "selector": "h1.product-title",
          "required": true
        },
        "summary": {
          "selector": ".product-summary",
          "required": false
        },
        "description": {
          "selector": ".product-description",
          "required": false
        },
        "price": {
          "selector": ".product-price",
          "required": false
        },
        "category": {
          "selector": ".product-category",
          "required": false
        },
        "tags": {
          "selector": ".product-tags .tag",
          "multiple": true,
          "required": false
        },
        "brand": {
          "selector": ".product-brand",
          "required": false
        },
        "image_urls": {
          "selector": ".product-images img",
          "attribute": "src",
          "multiple": true,
          "required": false
        },
        "specs": {
          "selector": ".product-specs",
          "required": false
        }
      }
    }
  }
]
```

## 使用方式

### 方式一：使用文件（推荐）

1. 在 `.env` 中启用目录加载：
   ```bash
   ENV_JSON_DIR=.env.json
   ```

2. 复制示例文件并修改：
   ```bash
   cp .env.json.example/CRAWLER_SITES_JSON.json .env.json/CRAWLER_SITES_JSON.json
   ```

3. 编辑配置文件添加你的站点

### 方式二：使用环境变量

在 `.env` 中直接设置（不推荐，配置复杂）：

```bash
CRAWLER_SITES_JSON='[{"id":"site1","name":"站点1",...}]'
```

## 常见场景

### 场景一：静态网站

```json
{
  "id": "static_site",
  "name": "静态商品站",
  "start_url": "https://static-shop.com",
  "is_spa": false,
  "extraction_config": {
    "mode": "selector",
    "fields": {
      "name": {"selector": "h1"},
      "price": {"selector": ".price"}
    }
  }
}
```

### 场景二：SPA 单页应用

```json
{
  "id": "spa_site",
  "name": "React商城",
  "start_url": "https://react-shop.com",
  "is_spa": true,
  "wait_for_selector": ".product-list",
  "wait_timeout": 15000,
  "extraction_config": {
    "mode": "selector",
    "fields": {
      "name": {"selector": "[data-testid='product-name']"}
    }
  }
}
```

### 场景三：限制爬取范围

```json
{
  "id": "limited_site",
  "name": "限制爬取",
  "start_url": "https://shop.com/products",
  "link_pattern": "^https://shop\\.com/products/.*",
  "max_depth": 2,
  "max_pages": 100,
  "crawl_delay": 2.0
}
```

## Cron 表达式示例

| 表达式 | 说明 |
|--------|------|
| `"0 2 * * *"` | 每天凌晨 2:00 |
| `"0 */6 * * *"` | 每 6 小时 |
| `"0 0 * * 0"` | 每周日凌晨 |
| `"0 0 1 * *"` | 每月 1 号凌晨 |

## 常见问题

### Q: 如何测试爬虫配置是否正确？

A: 可以通过 API 手动触发爬取任务并查看日志。

### Q: 如何处理需要登录的网站？

A: 目前不支持需要登录的网站，建议使用公开可访问的商品页面。

### Q: 如何提取动态加载的内容？

A: 设置 `is_spa: true` 并配置 `wait_for_selector` 等待内容加载完成。

### Q: 爬取失败如何排查？

A: 检查以下几点：
1. URL 是否可访问
2. CSS 选择器是否正确
3. 是否需要等待动态内容加载
4. 查看爬虫日志获取详细错误信息

## 相关配置

- `CRAWLER_DATABASE_PATH`: 爬虫数据库路径
- 爬虫相关的其他环境变量请查看 `.env.example`
