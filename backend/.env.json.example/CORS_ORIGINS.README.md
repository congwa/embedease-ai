# CORS_ORIGINS.json 配置说明

## 文件作用

配置允许跨域访问的源（Origin）列表，用于控制哪些前端域名可以访问后端 API。

## 什么是 CORS

CORS（Cross-Origin Resource Sharing，跨域资源共享）是一种安全机制，用于控制不同域名之间的资源访问。

### 为什么需要 CORS 配置

当前端和后端部署在不同域名时（例如前端在 `http://localhost:3000`，后端在 `http://localhost:8000`），浏览器会阻止前端访问后端 API，除非后端明确允许该域名。

## 配置格式

```json
[
  "http://localhost:3000",
  "https://yourdomain.com"
]
```

简单的字符串数组，每个元素是一个允许的源。

## 配置示例

### 开发环境

```json
[
  "http://localhost:3000",
  "http://localhost:3001",
  "http://127.0.0.1:3000"
]
```

### 生产环境

```json
[
  "https://www.yourdomain.com",
  "https://app.yourdomain.com",
  "https://admin.yourdomain.com"
]
```

### 混合环境

```json
[
  "http://localhost:3000",
  "https://staging.yourdomain.com",
  "https://www.yourdomain.com"
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
   cp .env.json.example/CORS_ORIGINS.json .env.json/CORS_ORIGINS.json
   ```

3. 编辑配置文件添加你的域名

### 方式二：使用环境变量

在 `.env` 中直接设置（适合简单配置）：

```bash
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

注意：环境变量使用逗号分隔，文件使用 JSON 数组格式。

## 配置规则

### 协议必须匹配

```json
// ✅ 正确
["http://localhost:3000", "https://yourdomain.com"]

// ❌ 错误：协议不匹配
["localhost:3000"]  // 缺少协议
```

### 端口必须明确

```json
// ✅ 正确
["http://localhost:3000"]

// ❌ 错误：端口不匹配
["http://localhost"]  // 如果前端运行在 3000 端口，这个配置无效
```

### 不要添加尾部斜杠

```json
// ✅ 正确
["http://localhost:3000"]

// ❌ 错误
["http://localhost:3000/"]  // 尾部斜杠会导致匹配失败
```

### 不支持通配符

```json
// ❌ 错误：不支持通配符
["http://*.yourdomain.com"]
["http://localhost:*"]
```

如需支持多个子域名，必须逐个列出：

```json
// ✅ 正确
[
  "https://app.yourdomain.com",
  "https://admin.yourdomain.com",
  "https://api.yourdomain.com"
]
```

## 安全建议

### 1. 生产环境不要使用 localhost

```json
// ❌ 生产环境不安全
[
  "http://localhost:3000",
  "https://yourdomain.com"
]

// ✅ 生产环境安全
[
  "https://yourdomain.com"
]
```

### 2. 使用 HTTPS

```json
// ❌ 生产环境不安全
["http://yourdomain.com"]

// ✅ 生产环境安全
["https://yourdomain.com"]
```

### 3. 不要使用 "*" 通配符

虽然技术上可以配置 `"*"` 允许所有域名，但这会带来严重的安全风险：

```json
// ❌ 极度不安全，不要这样做
["*"]
```

### 4. 最小权限原则

只添加真正需要访问的域名：

```json
// ✅ 只允许必要的域名
[
  "https://www.yourdomain.com",
  "https://app.yourdomain.com"
]
```

## 常见场景

### 场景一：本地开发

```json
[
  "http://localhost:3000",
  "http://localhost:3001",
  "http://127.0.0.1:3000"
]
```

### 场景二：多环境部署

```json
[
  "http://localhost:3000",           // 本地开发
  "https://dev.yourdomain.com",      // 开发环境
  "https://staging.yourdomain.com",  // 测试环境
  "https://www.yourdomain.com"       // 生产环境
]
```

### 场景三：多个前端应用

```json
[
  "https://www.yourdomain.com",      // 主站
  "https://app.yourdomain.com",      // Web 应用
  "https://admin.yourdomain.com",    // 管理后台
  "https://mobile.yourdomain.com"    // 移动端 H5
]
```

## 常见问题

### Q: 为什么配置了还是跨域错误？

A: 检查以下几点：
1. 协议是否匹配（http vs https）
2. 端口是否正确
3. 是否有尾部斜杠
4. 是否重启了后端服务
5. 浏览器控制台查看具体的 Origin 值

### Q: 如何允许所有本地端口？

A: CORS 不支持通配符，必须逐个添加：

```json
[
  "http://localhost:3000",
  "http://localhost:3001",
  "http://localhost:8080"
]
```

### Q: 开发环境和生产环境如何区分？

A: 使用不同的配置文件或环境变量：

```bash
# 开发环境 .env.development
CORS_ORIGINS=http://localhost:3000

# 生产环境 .env.production
CORS_ORIGINS=https://yourdomain.com
```

### Q: 如何调试 CORS 问题？

A: 
1. 打开浏览器开发者工具
2. 查看 Network 标签
3. 找到失败的请求
4. 查看 Response Headers 中的 `Access-Control-Allow-Origin`
5. 对比请求的 Origin 和允许的 Origin

### Q: 移动应用需要配置 CORS 吗？

A: 不需要。CORS 是浏览器的安全机制，原生移动应用（iOS/Android）不受此限制。

## 相关配置

- `API_HOST`: API 服务监听地址
- `API_PORT`: API 服务监听端口
- FastAPI 的其他 CORS 相关配置

## 技术细节

配置在代码中的使用：

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # 使用此配置
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 参考资料

- [MDN - CORS](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/CORS)
- [FastAPI - CORS](https://fastapi.tiangolo.com/tutorial/cors/)
