/**
 * @embedease/chat-sdk-react
 *
 * React Hooks for Chat SDK
 */

// Hooks
export { useTimeline, type UseTimelineOptions, type UseTimelineReturn } from "./use-timeline";
export { useChat, type UseChatOptions, type UseChatReturn } from "./use-chat";
export { useWebSocket, type UseWebSocketOptions, type UseWebSocketReturn } from "./use-websocket";

// Re-export core types from SDK
export {
  type TimelineState,
  type TimelineItem,
  type ChatEvent,
  type ChatRequest,
  type ImageAttachment,
  type HistoryMessage,
  type ConnectionState,
  type WSMessage,
} from "@embedease/chat-sdk";
