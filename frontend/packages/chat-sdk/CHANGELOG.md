# Changelog

All notable changes to `@embedease/chat-sdk` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.15] - 2025-01-31

### Added

- **初始版本发布**
- `ChatClient` - SSE 流式聊天客户端
  - `stream()` - 发送消息并获取流式响应
  - `streamWithTimeline()` - 带 Timeline 状态管理的流式聊天
  - `abort()` - 中止当前流
- **Timeline 模块** - 聊天消息状态管理
  - `createInitialState()` - 创建初始状态
  - `timelineReducer()` - 事件处理 reducer
  - `addUserMessage()` / `startAssistantTurn()` / `endTurn()` - Action 函数
  - `historyToTimeline()` - 历史消息转换
- **WebSocket 模块** - 实时双向通信
  - `WebSocketManager` - 连接管理器
  - 指数退避重连
  - 心跳保活
  - 离线消息队列
  - `createUserWebSocketManager()` / `createAgentWebSocketManager()` - 工厂函数
- **Core 模块** - 事件类型和 Payload 定义
