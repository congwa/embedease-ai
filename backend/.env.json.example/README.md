# ENV_JSON 配置目录

本目录用于存放格式化的 JSON 配置文件，提升复杂配置的可读性和可维护性。

## 快速开始

### 1. 启用 .env.json 目录

在 `.env` 文件中设置：

```bash
ENV_JSON_DIR=.env.json
```

### 2. 复制示例配置

```bash
cp -r .env.json.example .env.json
```

### 3. 根据需要修改配置文件

## 配置文件说明

本目录包含 4 个配置文件，每个文件都有详细的使用说明：

| 配置文件 | 用途 | 详细文档 |
|---------|------|---------|
| `MODEL_PROFILES_JSON.json` | 模型能力配置（覆盖 models.dev） | [查看详情](./MODEL_PROFILES_JSON.README.md) |
| `CRAWLER_SITES_JSON.json` | 爬虫站点配置 | [查看详情](./CRAWLER_SITES_JSON.README.md) |
| `DEFAULT_AGENTS_JSON.json` | Agent 助手配置 | [查看详情](./DEFAULT_AGENTS_JSON.README.md) |
| `CORS_ORIGINS.json` | CORS 跨域配置 | [查看详情](./CORS_ORIGINS.README.md) |

## 核心概念

### 文件命名规则

文件名必须与环境变量名完全一致：`<ENV_VAR_NAME>.json`

### 加载优先级

```
.env 环境变量 > .env.json 目录文件 > 默认值
```

### 注释支持

JSON 文件支持 `//` 单行注释（运行时自动剥离）：

```json
{
  // 这是注释
  "key": "value"  // 行尾注释
}
```

**注意**：IDE 可能报错，但运行时正常工作。

## 最佳实践

### 1. 版本控制
- ✅ 将 `.env.json/` 纳入 Git（业务配置）
- ❌ 不要提交 `.env`（敏感信息）

### 2. 环境隔离
- **开发环境**：使用 `.env.json/` 文件配置
- **生产环境**：使用 `.env` 环境变量覆盖

### 3. 配置分离
- **敏感信息**（API Key）→ `.env`
- **业务配置**（站点规则、模型能力）→ `.env.json/`

### 4. 临时测试

在 `.env` 中临时覆盖文件配置：

```bash
# 临时覆盖，测试完删除即可
MODEL_PROFILES_JSON='{"test/model": {"tool_calling": true}}'
```

## 故障排查

配置未生效？检查以下几点：

1. ✅ `.env` 中是否设置了 `ENV_JSON_DIR=.env.json`
2. ✅ JSON 文件名是否与环境变量名完全一致
3. ✅ JSON 格式是否正确（使用在线工具验证）
4. ✅ 是否有 `.env` 中的同名变量覆盖了文件配置
5. ✅ 是否重启了后端服务

## 更多帮助

- 查看各配置文件的详细 README
- 查看 `.env.example` 了解所有环境变量
- 遇到问题请查看应用日志
