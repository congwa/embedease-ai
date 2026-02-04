/**
 * Client 模块统一导出
 */

// SSE 客户端
export {
  streamChat,
  ChatClient,
  type StreamChatController,
  type StreamChatOptions,
  type StreamWithTimelineResult,
} from "./sse-client";

// WebSocket 管理器
export {
  WebSocketManager,
  createUserWebSocketManager,
  createAgentWebSocketManager,
  type ConnectionState,
  type WSMessage,
  type WebSocketConfig,
  type MessageHandler,
  type StateChangeHandler,
  type ErrorHandler,
  WS_PROTOCOL_VERSION,
} from "./websocket";
