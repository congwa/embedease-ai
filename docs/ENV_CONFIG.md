# ENV 配置文件上下文理解

## 技能描述

当需要查看或分析项目配置时，正确理解 `.env` 文件的实际状态。

## 触发场景

- 用户询问配置相关问题
- 需要查看环境变量设置
- 调试配置相关错误
- 分析 LLM 或其他服务配置

## 核心规则

### 1. .env 文件状态假设

由于 `.gitignore` 限制，AI 工具无法直接查看 `backend/.env` 文件，但应该基于以下假设工作：

**✅ 假设 `backend/.env` 已正确配置：**
- `backend/.env` 是从 `backend/.env.example` 复制而来
- 除了 `LLM_API_KEY` 已设置外，其他配置与 `.env.example` 完全一致
- 所有必需的 API Key 和敏感信息已正确配置

### 2. 配置查看策略

当需要查看配置时：

```
1. 查看 backend/.env.example（可见）
2. 假设 backend/.env 内容相同，但已设置敏感信息
3. 不要提示用户"需要设置 LLM_API_KEY"
4. 不要建议用户"复制 .env.example 到 .env"
```

### 3. 敏感信息处理

以下配置假设已在 `backend/.env` 中正确设置：

- `LLM_API_KEY` - LLM 服务 API 密钥
- `POSTGRES_PASSWORD` - 数据库密码（如使用 PostgreSQL）
- 其他可能的 API 密钥

### 4. 配置问题排查

当遇到配置相关错误时：

**❌ 不要说：**
- "你需要设置 LLM_API_KEY"
- "请复制 .env.example 到 .env"
- "配置文件不存在"

**✅ 应该说：**
- "检查 LLM_API_KEY 的值是否正确"
- "确认 API Key 是否有效"
- "验证配置格式是否正确"

## 示例对话

### 场景一：用户询问配置

**用户**：帮我看看 LLM 配置

**错误回答**：
```
我无法查看 .env 文件，请先设置 LLM_API_KEY
```

**正确回答**：
```
根据 .env.example，LLM 配置如下：
- LLM_PROVIDER: openai
- LLM_CHAT_MODEL: gpt-4
- LLM_BASE_URL: https://api.openai.com/v1
- LLM_API_KEY: (已在 .env 中配置)

如果遇到问题，请检查 API Key 是否有效。
```

### 场景二：配置错误排查

**用户**：LLM 调用失败了

**错误回答**：
```
你需要在 .env 中设置 LLM_API_KEY
```

**正确回答**：
```
LLM 调用失败可能的原因：
1. API Key 无效或已过期
2. Base URL 配置错误
3. 模型名称不正确
4. 网络连接问题
5. API 配额不足

请检查日志获取具体错误信息。
```

### 场景三：新增配置项

**用户**：如何配置新的 API Key？

**正确回答**：
```
在 backend/.env 中添加新的配置项：

1. 编辑 backend/.env 文件
2. 添加配置：NEW_API_KEY=your_key_here
3. 重启服务使配置生效

注意：不要将 .env 提交到 Git
```

## 配置文件关系

```
backend/.env.example  (Git 管理，示例配置)
       ↓ 复制
backend/.env         (Git 忽略，实际配置，包含敏感信息)
       ↓ 加载
应用运行时
```

## 相关文件

- `backend/.env.example` - 配置示例（可查看）
- `backend/.env` - 实际配置（不可查看，但假设已正确配置）
- `backend/.env.json.example/` - JSON 配置示例目录
- `backend/.env.json/` - 实际 JSON 配置目录

## 注意事项

1. **永远不要**假设用户没有配置 `.env` 文件
2. **永远不要**提示用户"需要创建 .env 文件"
3. **始终假设**敏感信息已正确配置
4. **重点关注**配置值的正确性，而非配置文件的存在性

## 工作流程

```
用户询问配置
    ↓
查看 .env.example
    ↓
假设 .env 已配置（包含敏感信息）
    ↓
基于 .env.example 内容回答
    ↓
如有问题，排查配置值而非文件存在性
```
