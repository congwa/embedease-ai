# ENV_JSON 配置目录

本目录用于存放格式化的 JSON 配置文件，提升复杂配置的可读性和可维护性。

## 使用方法

### 1. 启用 .env.json 目录

在 `.env` 文件中设置：

```bash
ENV_JSON_DIR=.env.json
```

### 2. 文件命名规则

文件名必须与对应的环境变量名完全一致，格式为：`<ENV_VAR_NAME>.json`

例如：
- `MODEL_PROFILES_JSON.json` 对应环境变量 `MODEL_PROFILES_JSON`
- `CRAWLER_SITES_JSON.json` 对应环境变量 `CRAWLER_SITES_JSON`
- `CORS_ORIGINS.json` 对应环境变量 `CORS_ORIGINS`

### 3. 加载优先级

配置加载遵循以下优先级（从高到低）：

1. **.env 中的环境变量**（内联 JSON 字符串）
2. **.env.json 目录中的 JSON 文件**
3. **默认值**

这意味着：
- 如果 `.env` 中设置了 `MODEL_PROFILES_JSON='{"model": {...}}'`，将使用该值
- 如果 `.env` 中未设置，但存在 `.env.json/MODEL_PROFILES_JSON.json`，将使用文件内容
- 如果都不存在，使用默认值（通常为空）

### 4. 支持的配置项

目前支持以下配置项：

#### MODEL_PROFILES_JSON.json
模型能力配置，用于手动指定模型特性（覆盖 models.dev 自动配置）

```json
{
  "moonshotai/Kimi-K2-Thinking": {
    "reasoning_output": true,
    "tool_calling": true,
    "structured_output": true
  }
}
```

#### CRAWLER_SITES_JSON.json
爬虫站点配置，定义要爬取的网站及其规则

```json
[
  {
    "id": "site_id",
    "name": "站点名称",
    "start_url": "https://example.com",
    "extraction_config": {
      "mode": "selector",
      "fields": { ... }
    }
  }
]
```

#### CORS_ORIGINS.json
CORS 跨域配置，允许的源列表

```json
[
  "http://localhost:3000",
  "https://yourdomain.com"
]
```

### 5. 注释支持

JSON 文件支持 `//` 单行注释（会在加载时自动剥离）：

```json
{
  // 这是一个注释
  "key": "value"  // 行尾注释
}
```

**注意**：IDE 可能会对注释报错，但运行时会正常工作。如果希望避免 lint 错误，请使用标准 JSON 格式（不含注释）。

### 6. 最佳实践

1. **版本控制**：将 `.env.json/` 目录纳入 Git 管理，方便团队协作和配置追踪
2. **环境隔离**：
   - 开发环境：使用 `.env.json/` 目录中的配置
   - 生产环境：使用 `.env` 环境变量覆盖（通过 CI/CD 注入）
3. **配置分离**：
   - 敏感信息（API Key）：仅放在 `.env` 中，不提交到 Git
   - 业务配置（站点规则、模型能力）：放在 `.env.json/` 中，提交到 Git
4. **格式化**：使用 IDE 的 JSON 格式化功能保持代码整洁

### 7. 故障排查

如果配置未生效，请检查：

1. `.env` 中是否设置了 `ENV_JSON_DIR`
2. JSON 文件名是否与环境变量名完全一致
3. JSON 文件格式是否正确（可用在线工具验证）
4. 是否有 `.env` 中的同名变量覆盖了文件配置

### 8. 示例：临时覆盖配置

开发时想临时测试新配置，无需修改文件：

```bash
# .env
ENV_JSON_DIR=.env.json

# 临时覆盖 MODEL_PROFILES_JSON.json 中的配置
MODEL_PROFILES_JSON='{"test/model": {"tool_calling": true}}'
```

这样可以快速测试，测试完成后删除 `.env` 中的该行即可恢复使用文件配置。
