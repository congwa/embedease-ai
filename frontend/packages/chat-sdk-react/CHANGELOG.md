# Changelog

All notable changes to `@embedease/chat-sdk-react` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.15] - 2025-01-31

### Added

- **初始版本发布**
- `useChat` Hook - 完整聊天功能
  - SSE 流式聊天
  - Timeline 状态管理
  - WebSocket 集成（可选）
  - `reload()` - 重新加载历史消息
  - `wsConnected` / `wsSendMessage` - WebSocket 状态和方法
- `useTimeline` Hook - 独立 Timeline 状态管理
  - `dispatch()` - 处理事件
  - `addUserMessage()` / `startAssistantTurn()` / `endTurn()` - Action 方法
  - `initFromHistory()` - 从历史消息初始化
- `useWebSocket` Hook - 独立 WebSocket 连接管理
  - 支持 user/agent 角色
  - 连接状态管理
  - 消息发送和接收
- 重新导出核心 SDK 类型

### Documentation

- README.md - 完整 API 文档和使用示例
- CHAT_IMPLEMENTATION_GUIDE.md - 聊天室实现指南
