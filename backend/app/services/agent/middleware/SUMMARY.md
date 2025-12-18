# Agent 中间件总览

本目录包含用于 LangChain Agent 的各种中间件实现。

## 可用中间件

### 1. ResponseSanitizationMiddleware (响应清洗)

**文件**: `response_sanitization.py`

**功能**: 检测并处理 LLM 返回的异常响应格式，确保用户始终看到友好的内容。

**使用场景**:
- 某些模型虽然支持 function calling，但返回非标准格式
- 防止用户看到技术性的、难以理解的内容
- 提升用户体验

**配置**:
```bash
RESPONSE_SANITIZATION_ENABLED=true
RESPONSE_SANITIZATION_CUSTOM_MESSAGE=  # 可选
```

**详细文档**: [README_RESPONSE_SANITIZATION.md](./README_RESPONSE_SANITIZATION.md)

---

### 2. IntentRecognitionMiddleware (意图识别)

**文件**: `intent_recognition.py`

**功能**: 在模型调用前识别用户意图，并根据意图动态调整可用工具列表。

**使用场景**:
- 优化工具选择，减少模型选择错误
- 提高响应速度
- 降低 token 消耗

**配置**:
```python
agent = await agent_service.get_agent(use_intent_recognition=True)
```

**详细文档**: [README_INTENT.md](./README_INTENT.md)

---

### 3. LoggingMiddleware (日志记录)

**文件**: `logging.py`

**功能**: 记录每次 LLM 调用的详细信息，包括输入、输出、耗时等。

**使用场景**:
- 调试和排查问题
- 性能监控
- 审计和合规

**特点**:
- 自动记录所有 LLM 调用
- 包含详细的上下文信息
- 支持结构化日志

---

### 4. SSEMiddleware (服务器推送事件)

**文件**: `llm_call_sse.py`

**功能**: 发送 `llm.call.start` 和 `llm.call.end` 事件，用于前端实时显示。

**使用场景**:
- 前端需要实时了解 LLM 调用状态
- 性能监控和调试
- 用户体验优化

**特点**:
- 轻量级事件推送
- 不干扰业务逻辑
- 可选启用

---

## 中间件执行顺序

中间件按照以下顺序执行（从外到内）：

```
请求流向 →

1. IntentRecognitionMiddleware    (意图识别，调整工具)
2. ResponseSanitizationMiddleware (响应清洗，检测异常)
3. SSEMiddleware                   (事件推送)
4. LoggingMiddleware               (日志记录)
5. → LLM 模型调用 ←
6. LoggingMiddleware               (记录响应)
7. SSEMiddleware                   (推送完成事件)
8. ResponseSanitizationMiddleware (清洗异常响应)
9. IntentRecognitionMiddleware    (透传)

← 响应流向
```

## 如何添加新中间件

### 1. 创建中间件文件

```python
# my_middleware.py
from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from collections.abc import Awaitable, Callable

class MyMiddleware(AgentMiddleware):
    """我的自定义中间件"""
    
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """处理模型调用"""
        # 前置处理
        print("Before LLM call")
        
        # 调用下一个中间件或模型
        response = await handler(request)
        
        # 后置处理
        print("After LLM call")
        
        return response
```

### 2. 在 Agent 中注册

在 `agent.py` 中添加：

```python
from app.services.agent.middleware.my_middleware import MyMiddleware

# 在 get_agent 方法中
middlewares = [
    MyMiddleware(),  # 添加你的中间件
    ResponseSanitizationMiddleware(),
    SSEMiddleware(),
    LoggingMiddleware(),
]
```

### 3. 添加测试

在 `tests/` 目录下创建测试文件：

```python
# tests/test_my_middleware.py
import pytest
from app.services.agent.middleware.my_middleware import MyMiddleware

def test_my_middleware():
    middleware = MyMiddleware()
    # ... 测试逻辑
```

### 4. 添加文档

创建 `README_MY_MIDDLEWARE.md` 说明中间件的功能和使用方法。

## 最佳实践

### 1. 职责单一

每个中间件应该只负责一个明确的功能：
- ✅ 好：ResponseSanitizationMiddleware 只负责清洗响应
- ❌ 差：一个中间件既记录日志又清洗响应

### 2. 不修改核心逻辑

中间件应该是可插拔的，不应该修改 Agent 的核心行为：
- ✅ 好：检测异常并替换内容
- ❌ 差：修改工具调用的核心逻辑

### 3. 性能优先

中间件会在每次 LLM 调用时执行，应该保持高性能：
- ✅ 好：使用正则表达式快速检测
- ❌ 差：复杂的 AI 分析或网络请求

### 4. 错误处理

中间件应该优雅地处理错误，不影响主流程：
- ✅ 好：捕获异常并记录，继续执行
- ❌ 差：抛出异常导致整个请求失败

### 5. 可配置

提供配置选项，让用户可以控制行为：
- ✅ 好：`enabled` 参数控制启用/禁用
- ❌ 差：硬编码行为，无法自定义

## 测试

运行所有中间件测试：

```bash
cd backend
uv run pytest tests/test_*middleware*.py -v
```

运行特定中间件测试：

```bash
uv run pytest tests/test_response_sanitization.py -v
```

## 监控和调试

### 查看日志

所有中间件都会记录日志到 `./logs/app.log`：

```bash
tail -f ./logs/app.log | grep middleware
```

### 获取统计信息

```python
from app.services.agent.middleware.response_sanitization import ResponseSanitizationMiddleware

# 获取统计
stats = ResponseSanitizationMiddleware.get_statistics()
print(stats)
```

## 常见问题

### Q: 中间件的执行顺序重要吗？

A: 是的！中间件按照注册顺序执行。通常：
1. 意图识别应该最先执行（调整工具）
2. 响应清洗应该在日志之前（避免记录异常内容）
3. 日志应该最后执行（记录最终状态）

### Q: 如何禁用某个中间件？

A: 大多数中间件都提供 `enabled` 参数：

```python
middleware = ResponseSanitizationMiddleware(enabled=False)
```

或者在配置文件中设置：

```bash
RESPONSE_SANITIZATION_ENABLED=false
```

### Q: 中间件会影响性能吗？

A: 影响很小。大多数中间件的开销 < 1ms，相比 LLM 调用（通常 1-5 秒）可以忽略。

### Q: 如何调试中间件？

A: 
1. 查看日志：`tail -f ./logs/app.log`
2. 使用测试脚本：`uv run python script/test-response-sanitization.py`
3. 添加 print 语句或断点

## 相关资源

- [LangChain Middleware 官方文档](https://python.langchain.com/docs/modules/agents/middleware)
- [Agent 架构文档](../README.md)
- [测试文件](../../../../tests/)

## 更新日志

### 2025-12-17
- ✨ 新增 ResponseSanitizationMiddleware
- 📝 完善中间件文档
- ✅ 添加完整测试覆盖

### 2025-12-16
- ✨ 新增 IntentRecognitionMiddleware
- 🔧 优化中间件执行顺序

