# Changelog

All notable changes to `langgraph-agent-kit` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.15] - 2025-01-31

### Added

- **初始版本发布**
- **Core 模块**
  - `AgentContext` - Agent 运行上下文
  - `EventEmitter` - 事件发射器
  - `StreamEvent` - 流式事件类型
- **Streaming 模块**
  - `StreamOrchestrator` - 流式编排器
  - `ResponseHandler` - 响应处理器
  - `SSEFormatter` - SSE 格式化器
- **Middleware 模块**
  - `BaseMiddleware` - 中间件基类
  - `MiddlewareRegistry` - 中间件注册表
  - 内置中间件：`LoggingMiddleware`, `SSEEventsMiddleware`
- **Tools 模块**
  - `BaseTool` - 工具基类
  - `ToolRegistry` - 工具注册表
  - `@tool` 装饰器
- **Integrations**
  - FastAPI 集成支持
