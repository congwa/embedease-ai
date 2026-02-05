# Changelog

All notable changes to `langgraph-agent-kit` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.17] - 2025-02-05

### Added

- **Chat Models 模块**
  - `V1ChatModel` / `is_v1_model` - v1 强制输出格式模型基类
  - `ReasoningChunk` / `BaseReasoningChatModel` / `StandardChatModel` - v0 兼容层
  - `SiliconFlowV1ChatModel` / `SiliconFlowReasoningChatModel` - 硅基流动推理模型
  - `create_chat_model()` - 统一模型创建工厂
  - `V0_REASONING_MODEL_REGISTRY` / `V1_REASONING_MODEL_REGISTRY` - 提供商注册表

- **Payload TypedDict**
  - 24 个类型安全的 Payload 定义
  - `MetaStartPayload`, `TextDeltaPayload`, `ToolStartPayload`, `ToolEndPayload`
  - `LlmCallStartPayload`, `LlmCallEndPayload`, `ErrorPayload`
  - `MemoryExtractionStartPayload`, `MemoryExtractionCompletePayload`
  - `AgentRoutedPayload`, `AgentHandoffPayload`, `AgentCompletePayload`
  - `SkillActivatedPayload`, `SkillLoadedPayload`, `TodosPayload` 等

- **Content Parser**
  - `parse_content_blocks()` / `parse_content_blocks_from_chunk()` - 内容解析
  - `ParsedContent` - 解析结果数据类
  - 类型守卫：`is_text_block`, `is_reasoning_block`, `is_tool_call_block`, `is_image_block`
  - `ContentBlock`, `TextContentBlock`, `ReasoningContentBlock`, `ToolCallBlock` 类型

### Changed

- **README.md 完善**：新增 Chat Models、Content Parser、Payload TypedDict、StreamingResponseHandler 文档

---

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
