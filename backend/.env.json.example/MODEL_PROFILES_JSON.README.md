# MODEL_PROFILES_JSON.json 配置说明

## 文件作用

用于**手动覆盖或补充 models.dev 的模型能力配置**，确保系统正确识别和使用 AI 模型的特性。

## 典型使用场景

1. **修正 models.dev 数据不准确**：当 models.dev 提供的模型能力信息有误时手动修正
2. **新模型支持**：为 models.dev 尚未收录的模型手动配置能力特性
3. **离线环境**：禁用 models.dev 后完全依赖本地配置
4. **测试调试**：临时修改模型能力进行功能测试

## 配置优先级

```
.env 中的 MODEL_PROFILES_JSON > .env.json/MODEL_PROFILES_JSON.json > models.dev API
```

## 配置格式

```json
{
  "模型标识符": {
    "reasoning_output": true/false,
    "tool_calling": true/false,
    "structured_output": true/false,
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
| `reasoning_output` | boolean | 模型是否支持推理输出（思维链） | 否 |
| `tool_calling` | boolean | 模型是否支持工具调用/函数调用 | 否 |
| `structured_output` | boolean | 模型是否支持结构化输出 | 否 |
| `temperature` | number | 默认温度参数（0-2） | 否 |
| `max_tokens` | number | 最大输出 token 数 | 否 |
| `max_completion_tokens` | number | 最大完成 token 数（部分模型） | 否 |

## 配置示例

```json
{
  "moonshotai/Kimi-K2-Thinking": {
    "reasoning_output": true,
    "tool_calling": true,
    "structured_output": true
  },
  "openai/o1": {
    "reasoning_output": true,
    "tool_calling": false,
    "structured_output": false
  },
  "deepseek/deepseek-chat": {
    "reasoning_output": false,
    "tool_calling": true,
    "structured_output": true,
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

## 使用方式

### 方式一：使用文件（推荐）

1. 在 `.env` 中启用目录加载：
   ```bash
   ENV_JSON_DIR=.env.json
   ```

2. 复制示例文件并修改：
   ```bash
   cp .env.json.example/MODEL_PROFILES_JSON.json .env.json/MODEL_PROFILES_JSON.json
   ```

3. 编辑 `.env.json/MODEL_PROFILES_JSON.json` 添加你的模型配置

### 方式二：使用环境变量

在 `.env` 中直接设置（适合临时测试）：

```bash
MODEL_PROFILES_JSON='{"test/model": {"tool_calling": true, "reasoning_output": false}}'
```

## 不配置的影响

### 启用 models.dev 时（默认）
- **无影响**：系统会从 `https://models.dev/api.json` 自动获取模型能力
- models.dev 提供大部分主流模型的配置

### 禁用 models.dev 时
- **可能影响功能**：
  - 系统无法识别模型是否支持工具调用
  - 系统无法识别模型是否支持推理输出
  - 系统无法识别模型是否支持结构化输出
  - 某些高级功能可能无法正常工作
  - LangChain 会使用默认行为（可能不准确）

## 代码中的使用

该配置在以下位置被使用：

1. **`app/core/config.py`** - 解析配置
   ```python
   @property
   def model_profiles(self) -> dict[str, dict[str, Any]]:
       parsed = self._load_json_from_env_or_file("MODEL_PROFILES_JSON", self.MODEL_PROFILES_JSON)
       return parsed or {}
   ```

2. **`app/core/llm.py`** - 创建 LLM 时应用配置
   ```python
   custom_profile = get_model_profile(
       model_name=model_name,
       env_profiles=settings.model_profiles,  # 使用此配置
   )
   ```

3. **`app/main.py`** - 启动时初始化并打印配置
   ```python
   def _init_model_profiles():
       # 拉取 models.dev 并与 env_profiles 合并
       pass
   ```

## 常见问题

### Q: 如何知道某个模型支持哪些能力？

A: 可以通过以下方式：
1. 查看 [models.dev](https://models.dev) 网站
2. 查阅模型官方文档
3. 启动应用时查看日志输出的模型配置

### Q: 配置后如何验证是否生效？

A: 启动应用后查看日志，会打印最终生效的模型配置：

```
INFO     models.dev 已启用，合并配置
         provider=openai
         model=gpt-4
         profile={'tool_calling': True, 'reasoning_output': False}
```

### Q: 能否只配置部分字段？

A: 可以。未配置的字段会使用 models.dev 的值或 LangChain 默认值。

### Q: 如何临时测试新配置？

A: 在 `.env` 中临时添加环境变量（优先级最高）：

```bash
MODEL_PROFILES_JSON='{"test/model": {"tool_calling": true}}'
```

测试完成后删除该行即可恢复文件配置。

## 相关配置

- `MODELS_DEV_ENABLED`: 是否启用 models.dev 自动拉取（默认 `true`）
- `MODELS_DEV_API_URL`: models.dev API 地址
- `MODELS_DEV_CACHE_TTL_SECONDS`: 缓存有效期（秒）
