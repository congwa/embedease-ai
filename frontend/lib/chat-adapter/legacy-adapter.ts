/**
 * 旧 SDK 适配器
 *
 * 封装现有代码，实现统一接口
 */

import {
  streamChat as legacyStreamChat,
  type StreamChatController,
} from "@/lib/api/chat";
import {
  createInitialState,
  addUserMessage as legacyAddUserMessage,
  startAssistantTurn as legacyStartAssistantTurn,
  timelineReducer as legacyTimelineReducer,
  clearTurn as legacyClearTurn,
  endTurn as legacyEndTurn,
  historyToTimeline as legacyHistoryToTimeline,
} from "@/lib/timeline-utils";
import {
  WebSocketManager as LegacyWebSocketManager,
  createUserWebSocketManager as legacyCreateUserWebSocketManager,
  createAgentWebSocketManager as legacyCreateAgentWebSocketManager,
} from "@/lib/websocket";
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
 * 旧 SDK SSE 客户端适配器
 *
 * 封装现有的 streamChat 函数，实现 IChatStreamClient 接口
 */
export class LegacyChatStreamClient implements IChatStreamClient {
  private controller: StreamChatController = { abort: () => {} };

  async *stream(
    request: ChatRequest
  ): AsyncGenerator<ChatEvent, void, unknown> {
    // 每次 stream 调用创建新的 controller
    this.controller = { abort: () => {} };
    yield* legacyStreamChat(request, this.controller);
  }

  abort(): void {
    this.controller.abort();
  }
}

// ==================== Timeline 管理器适配器 ====================

/**
 * 旧 SDK Timeline 管理器适配器
 *
 * 封装现有的 timeline reducer 和 actions，实现 ITimelineManager 接口
 */
export class LegacyTimelineManager implements ITimelineManager {
  private state: TimelineState = createInitialState();

  getState(): TimelineState {
    return this.state;
  }

  setState(state: TimelineState): void {
    this.state = state;
  }

  dispatch(event: ChatEvent): void {
    this.state = legacyTimelineReducer(this.state, event);
  }

  addUserMessage(
    id: string,
    content: string,
    images?: ImageAttachment[]
  ): void {
    this.state = legacyAddUserMessage(this.state, id, content, images);
  }

  startAssistantTurn(turnId: string): void {
    this.state = legacyStartAssistantTurn(this.state, turnId);
  }

  clearTurn(turnId: string): void {
    this.state = legacyClearTurn(this.state, turnId);
  }

  endTurn(): void {
    this.state = legacyEndTurn(this.state);
  }

  reset(): void {
    this.state = createInitialState();
  }

  initFromHistory(messages: HistoryMessage[]): void {
    this.state = legacyHistoryToTimeline(messages);
  }
}

// ==================== WebSocket 管理器适配器 ====================

/**
 * 旧 SDK WebSocket 管理器适配器
 *
 * 直接使用现有的 WebSocketManager，因为接口已经兼容
 */
export class LegacyWebSocketManagerAdapter implements IWebSocketManager {
  private manager: LegacyWebSocketManager;

  constructor(manager: LegacyWebSocketManager) {
    this.manager = manager;
  }

  getState(): ConnectionState {
    return this.manager.getState();
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
    return this.manager.onMessage(handler);
  }

  onStateChange(
    handler: (state: ConnectionState, prevState: ConnectionState) => void
  ): () => void {
    return this.manager.onStateChange(handler);
  }

  onError(handler: (error: Error) => void): () => void {
    return this.manager.onError(handler);
  }

  destroy(): void {
    this.manager.destroy();
  }
}

// ==================== 工厂函数 ====================

export function createLegacyUserWebSocketManager(
  baseUrl: string,
  conversationId: string,
  userId: string
): IWebSocketManager {
  const manager = legacyCreateUserWebSocketManager(
    baseUrl,
    conversationId,
    userId
  );
  return new LegacyWebSocketManagerAdapter(manager);
}

export function createLegacyAgentWebSocketManager(
  baseUrl: string,
  conversationId: string,
  agentId: string
): IWebSocketManager {
  const manager = legacyCreateAgentWebSocketManager(
    baseUrl,
    conversationId,
    agentId
  );
  return new LegacyWebSocketManagerAdapter(manager);
}
