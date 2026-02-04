/**
 * Chat Adapter 统一接口定义
 */

import type { ChatEvent, ChatRequest, ImageAttachment } from "@/types/chat";
import type { TimelineState } from "@/lib/timeline/types";
import type { Product } from "@/types/product";

// ==================== 历史消息类型 ====================

export interface HistoryMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  products?: Product[];
  message_type?: string;
  extra_metadata?: {
    greeting_config?: {
      title?: string;
      subtitle?: string;
      body?: string;
    };
    cta?: { text: string; payload: string };
    delay_ms?: number;
    channel?: string;
  };
}

// ==================== Chat 客户端接口 ====================

/**
 * SSE 流式聊天客户端统一接口
 */
export interface IChatStreamClient {
  /**
   * 发送消息并获取流式响应
   * @returns AsyncGenerator，逐个产出 ChatEvent
   */
  stream(request: ChatRequest): AsyncGenerator<ChatEvent, void, unknown>;

  /**
   * 中止当前流
   */
  abort(): void;
}

// ==================== Timeline 管理器接口 ====================

/**
 * Timeline 状态管理器统一接口
 */
export interface ITimelineManager {
  /** 获取当前状态（不可变） */
  getState(): TimelineState;

  /** 设置状态（替换） */
  setState(state: TimelineState): void;

  /** 处理 ChatEvent，更新状态 */
  dispatch(event: ChatEvent): void;

  /** 添加用户消息 */
  addUserMessage(id: string, content: string, images?: ImageAttachment[]): void;

  /** 开始助手回复 Turn */
  startAssistantTurn(turnId: string): void;

  /** 清除指定 Turn */
  clearTurn(turnId: string): void;

  /** 结束当前 Turn */
  endTurn(): void;

  /** 重置为初始状态 */
  reset(): void;

  /** 从历史消息初始化 */
  initFromHistory(messages: HistoryMessage[]): void;
}

// ==================== WebSocket 管理器接口 ====================

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

export interface WSMessage {
  v: number;
  id: string;
  ts: number;
  action: string;
  payload: Record<string, unknown>;
  conversation_id?: string;
}

/**
 * WebSocket 管理器统一接口
 */
export interface IWebSocketManager {
  /** 获取连接状态 */
  getState(): ConnectionState;

  /** 获取连接 ID */
  getConnectionId(): string | null;

  /** 获取会话 ID */
  getConversationId(): string | null;

  /** 是否已连接 */
  isConnected(): boolean;

  /** 建立连接 */
  connect(): void;

  /** 断开连接 */
  disconnect(): void;

  /** 发送消息 */
  send(action: string, payload: Record<string, unknown>): string;

  /** 添加消息监听器 */
  onMessage(handler: (message: WSMessage) => void): () => void;

  /** 添加状态变更监听器 */
  onStateChange(
    handler: (state: ConnectionState, prevState: ConnectionState) => void
  ): () => void;

  /** 添加错误监听器 */
  onError(handler: (error: Error) => void): () => void;

  /** 销毁实例 */
  destroy(): void;
}
