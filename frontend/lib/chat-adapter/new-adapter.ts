/**
 * 新 SDK 适配器
 *
 * 使用 @embedease/chat-sdk 包实现
 */

import {
  ChatClient,
  createInitialState,
  addUserMessage as sdkAddUserMessage,
  startAssistantTurn as sdkStartAssistantTurn,
  timelineReducer as sdkTimelineReducer,
  clearTurn as sdkClearTurn,
  endTurn as sdkEndTurn,
  historyToTimeline as sdkHistoryToTimeline,
  createUserWebSocketManager as sdkCreateUserWebSocketManager,
  createAgentWebSocketManager as sdkCreateAgentWebSocketManager,
  type WebSocketManager as SDKWebSocketManager,
} from "@embedease/chat-sdk";

import type { ChatEvent, ChatRequest, ImageAttachment } from "@/types/chat";
import type { TimelineState } from "@/lib/timeline/types";
import type {
  IChatStreamClient,
  ITimelineManager,
  IWebSocketManager,
  HistoryMessage,
  WSMessage,
  ConnectionState,
} from "./types";

// ==================== SSE 客户端适配器 ====================

/**
 * 新 SDK SSE 客户端适配器
 */
export class NewChatStreamClient implements IChatStreamClient {
  private client: ChatClient;

  constructor(baseUrl: string) {
    this.client = new ChatClient({ baseUrl });
  }

  async *stream(
    request: ChatRequest
  ): AsyncGenerator<ChatEvent, void, unknown> {
    yield* this.client.stream(request) as AsyncGenerator<ChatEvent, void, unknown>;
  }

  abort(): void {
    this.client.abort();
  }
}

// ==================== Timeline 管理器适配器 ====================

/**
 * 新 SDK Timeline 管理器适配器
 */
export class NewTimelineManager implements ITimelineManager {
  private state: TimelineState = createInitialState() as TimelineState;

  getState(): TimelineState {
    return this.state;
  }

  setState(state: TimelineState): void {
    this.state = state;
  }

  dispatch(event: ChatEvent): void {
    this.state = sdkTimelineReducer(this.state as never, event as never) as TimelineState;
  }

  addUserMessage(
    id: string,
    content: string,
    images?: ImageAttachment[]
  ): void {
    this.state = sdkAddUserMessage(this.state as never, id, content, images as never) as TimelineState;
  }

  startAssistantTurn(turnId: string): void {
    this.state = sdkStartAssistantTurn(this.state as never, turnId) as TimelineState;
  }

  clearTurn(turnId: string): void {
    this.state = sdkClearTurn(this.state as never, turnId) as TimelineState;
  }

  endTurn(): void {
    this.state = sdkEndTurn(this.state as never) as TimelineState;
  }

  reset(): void {
    this.state = createInitialState() as TimelineState;
  }

  initFromHistory(messages: HistoryMessage[]): void {
    this.state = sdkHistoryToTimeline(messages as never) as TimelineState;
  }
}

// ==================== WebSocket 管理器适配器 ====================

/**
 * 新 SDK WebSocket 管理器适配器
 */
export class NewWebSocketManagerAdapter implements IWebSocketManager {
  private manager: SDKWebSocketManager;

  constructor(manager: SDKWebSocketManager) {
    this.manager = manager;
  }

  getState(): ConnectionState {
    return this.manager.getState() as ConnectionState;
  }

  getConnectionId(): string | null {
    return this.manager.getConnectionId();
  }

  getConversationId(): string | null {
    return this.manager.getConversationId();
  }

  isConnected(): boolean {
    return this.manager.isConnected();
  }

  connect(): void {
    this.manager.connect();
  }

  disconnect(): void {
    this.manager.disconnect();
  }

  send(action: string, payload: Record<string, unknown>): string {
    return this.manager.send(action, payload);
  }

  onMessage(handler: (message: WSMessage) => void): () => void {
    return this.manager.onMessage(handler as never);
  }

  onStateChange(
    handler: (state: ConnectionState, prevState: ConnectionState) => void
  ): () => void {
    return this.manager.onStateChange(handler as never);
  }

  onError(handler: (error: Error) => void): () => void {
    return this.manager.onError(handler);
  }

  destroy(): void {
    this.manager.destroy();
  }
}

// ==================== 工厂函数 ====================

export function createNewUserWebSocketManager(
  baseUrl: string,
  conversationId: string,
  userId: string
): IWebSocketManager {
  const manager = sdkCreateUserWebSocketManager(baseUrl, conversationId, userId);
  return new NewWebSocketManagerAdapter(manager);
}

export function createNewAgentWebSocketManager(
  baseUrl: string,
  conversationId: string,
  agentId: string
): IWebSocketManager {
  const manager = sdkCreateAgentWebSocketManager(baseUrl, conversationId, agentId);
  return new NewWebSocketManagerAdapter(manager);
}
