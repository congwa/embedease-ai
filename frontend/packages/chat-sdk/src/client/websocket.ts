/**
 * WebSocket 连接管理器
 *
 * 提供：
 * - 连接状态机管理
 * - 指数退避重连
 * - 心跳保活
 * - 离线消息队列
 * - 事件分发
 */

// ============ 类型定义 ============

export const WS_PROTOCOL_VERSION = 1;

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
  reply_to?: string;
  error?: {
    code: string;
    message: string;
    detail?: unknown;
  };
}

export interface WebSocketConfig {
  baseUrl: string;
  endpoint: string;
  token: string;
  pingInterval?: number;
  pongTimeout?: number;
  maxReconnectAttempts?: number;
  initialReconnectDelay?: number;
  maxReconnectDelay?: number;
}

export type MessageHandler = (message: WSMessage) => void;
export type StateChangeHandler = (
  state: ConnectionState,
  prevState: ConnectionState
) => void;
export type ErrorHandler = (error: Error) => void;

// ============ 工具函数 ============

function generateId(): string {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function buildMessage(
  action: string,
  payload: Record<string, unknown>,
  conversationId?: string
): WSMessage {
  return {
    v: WS_PROTOCOL_VERSION,
    id: generateId(),
    ts: Date.now(),
    action,
    payload,
    conversation_id: conversationId,
  };
}

// ============ WebSocketManager 类 ============

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private state: ConnectionState = "disconnected";

  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private pongTimer: ReturnType<typeof setTimeout> | null = null;
  private lastPongAt = 0;

  private messageQueue: WSMessage[] = [];
  private readonly maxQueueSize = 100;

  private messageHandlers = new Set<MessageHandler>();
  private stateChangeHandlers = new Set<StateChangeHandler>();
  private errorHandlers = new Set<ErrorHandler>();

  private connectionId: string | null = null;
  private conversationId: string | null = null;

  constructor(config: WebSocketConfig) {
    this.config = {
      baseUrl: config.baseUrl,
      endpoint: config.endpoint,
      token: config.token,
      pingInterval: config.pingInterval ?? 30000,
      pongTimeout: config.pongTimeout ?? 10000,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 10,
      initialReconnectDelay: config.initialReconnectDelay ?? 1000,
      maxReconnectDelay: config.maxReconnectDelay ?? 30000,
    };

    const match = config.endpoint.match(/\/(user|agent)\/([^?]+)/);
    if (match) {
      this.conversationId = match[2];
    }

    if (typeof window !== "undefined") {
      window.addEventListener("online", this.handleOnline);
      window.addEventListener("offline", this.handleOffline);
    }
  }

  getState(): ConnectionState {
    return this.state;
  }

  getConnectionId(): string | null {
    return this.connectionId;
  }

  getConversationId(): string | null {
    return this.conversationId;
  }

  isConnected(): boolean {
    return this.state === "connected" && this.ws?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.state === "connecting" || this.state === "connected") {
      return;
    }
    this.doConnect();
  }

  disconnect(): void {
    this.cleanup();
    this.setState("disconnected");
  }

  send(action: string, payload: Record<string, unknown>): string {
    const message = buildMessage(action, payload, this.conversationId ?? undefined);

    if (this.isConnected()) {
      this.doSend(message);
    } else {
      this.enqueueMessage(message);
    }

    return message.id;
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onStateChange(handler: StateChangeHandler): () => void {
    this.stateChangeHandlers.add(handler);
    return () => this.stateChangeHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  destroy(): void {
    this.disconnect();
    this.messageHandlers.clear();
    this.stateChangeHandlers.clear();
    this.errorHandlers.clear();

    if (typeof window !== "undefined") {
      window.removeEventListener("online", this.handleOnline);
      window.removeEventListener("offline", this.handleOffline);
    }
  }

  // ============ 私有方法 ============

  private setState(newState: ConnectionState): void {
    if (this.state === newState) return;

    const prevState = this.state;
    this.state = newState;

    for (const handler of this.stateChangeHandlers) {
      try {
        handler(newState, prevState);
      } catch (e) {
        console.error("[WS] State change handler error:", e);
      }
    }
  }

  private doConnect(): void {
    this.setState("connecting");

    try {
      const url = `${this.config.baseUrl}${this.config.endpoint}?token=${encodeURIComponent(this.config.token)}`;
      this.ws = new WebSocket(url);

      this.ws.onopen = this.handleOpen;
      this.ws.onmessage = this.handleMessage;
      this.ws.onclose = this.handleClose;
      this.ws.onerror = this.handleError;
    } catch (e) {
      this.setState("disconnected");
      this.scheduleReconnect();
    }
  }

  private handleOpen = (): void => {
    this.setState("connected");
    this.reconnectAttempts = 0;
    this.lastPongAt = Date.now();
    this.startPing();
    this.flushMessageQueue();
  };

  private handleMessage = (event: MessageEvent): void => {
    try {
      const message: WSMessage = JSON.parse(event.data);

      if (message.action === "system.connected") {
        this.connectionId =
          (message.payload as { connection_id?: string }).connection_id ?? null;
      } else if (message.action === "system.pong") {
        this.lastPongAt = Date.now();
        if (this.pongTimer) {
          clearTimeout(this.pongTimer);
          this.pongTimer = null;
        }
        return;
      }

      for (const handler of this.messageHandlers) {
        try {
          handler(message);
        } catch (e) {
          console.error("[WS] Message handler error:", e);
        }
      }
    } catch (e) {
      console.error("[WS] Failed to parse message:", e);
    }
  };

  private handleClose = (event: CloseEvent): void => {
    this.cleanup();

    if (event.code === 1000 || event.code === 1001) {
      this.setState("disconnected");
    } else {
      this.scheduleReconnect();
    }
  };

  private handleError = (): void => {
    const error = new Error("WebSocket error");
    for (const handler of this.errorHandlers) {
      try {
        handler(error);
      } catch (e) {
        console.error("[WS] Error handler error:", e);
      }
    }
  };

  private handleOnline = (): void => {
    if (this.state === "disconnected" || this.state === "reconnecting") {
      this.reconnectAttempts = 0;
      this.doConnect();
    }
  };

  private handleOffline = (): void => {
    this.cleanup();
    this.setState("disconnected");
  };

  private cleanup(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      if (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      ) {
        this.ws.close(1000, "Client disconnect");
      }
      this.ws = null;
    }
    this.connectionId = null;
  }

  private startPing(): void {
    if (this.pingTimer) return;

    this.pingTimer = setInterval(() => {
      if (!this.isConnected()) return;

      const message = buildMessage("system.ping", {});
      this.doSend(message);

      this.pongTimer = setTimeout(() => {
        this.ws?.close(4000, "Pong timeout");
      }, this.config.pongTimeout);
    }, this.config.pingInterval);
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.setState("disconnected");
      return;
    }

    this.setState("reconnecting");

    const delay = Math.min(
      this.config.initialReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.config.maxReconnectDelay
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.doConnect();
    }, delay);
  }

  private doSend(message: WSMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private enqueueMessage(message: WSMessage): void {
    if (this.messageQueue.length >= this.maxQueueSize) {
      this.messageQueue.shift();
    }
    this.messageQueue.push(message);
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.doSend(message);
      }
    }
  }
}

// ============ 工厂函数 ============

export function createUserWebSocketManager(
  baseUrl: string,
  conversationId: string,
  userId: string
): WebSocketManager {
  return new WebSocketManager({
    baseUrl,
    endpoint: `/ws/user/${conversationId}`,
    token: userId,
  });
}

export function createAgentWebSocketManager(
  baseUrl: string,
  conversationId: string,
  agentId: string
): WebSocketManager {
  return new WebSocketManager({
    baseUrl,
    endpoint: `/ws/agent/${conversationId}`,
    token: agentId,
  });
}
