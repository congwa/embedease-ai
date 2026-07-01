/**
 * WebSocket 连接管理器
 * 
 * 统一管理 WebSocket 连接的生命周期，提供：
 * - 连接状态机管理
 * - 指数退避重连
 * - 心跳保活
 * - 离线消息队列
 * - 事件分发
 */

import { WS_PROTOCOL_VERSION } from "@/types/websocket";

// ============ 类型定义 ============

/** 连接状态 */
export type ConnectionState = 
  | "disconnected"  // 断开
  | "connecting"    // 连接中
  | "connected"     // 已连接
  | "reconnecting"; // 重连中

/** WebSocket 消息类型 */
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

/** 连接配置 */
export interface WebSocketConfig {
  /** WebSocket 基础 URL */
  baseUrl: string;
  /** 端点路径 (如 /ws/user/{conversationId} 或 /ws/agent/{conversationId}) */
  endpoint: string;
  /** 认证 token */
  token: string;
  /** 心跳间隔 (毫秒)，默认 30000 */
  pingInterval?: number;
  /** 心跳超时 (毫秒)，默认 10000 */
  pongTimeout?: number;
  /** 最大重连次数，默认 10 */
  maxReconnectAttempts?: number;
  /** 初始重连延迟 (毫秒)，默认 1000 */
  initialReconnectDelay?: number;
  /** 最大重连延迟 (毫秒)，默认 30000 */
  maxReconnectDelay?: number;
}

/** 事件监听器类型 */
export type MessageHandler = (message: WSMessage) => void;
export type StateChangeHandler = (state: ConnectionState, prevState: ConnectionState) => void;
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
  
  // 重连相关
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  
  // 心跳相关
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private pongTimer: ReturnType<typeof setTimeout> | null = null;
  private lastPongAt = 0;
  
  // 消息队列 (离线时缓存)
  private messageQueue: WSMessage[] = [];
  private readonly maxQueueSize = 100;
  
  // 事件监听器
  private messageHandlers = new Set<MessageHandler>();
  private stateChangeHandlers = new Set<StateChangeHandler>();
  private errorHandlers = new Set<ErrorHandler>();
  
  // 连接信息
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
    
    // 从 endpoint 提取 conversationId
    const match = config.endpoint.match(/\/(user|agent)\/([^?]+)/);
    if (match) {
      this.conversationId = match[2];
    }
    
    // 监听网络状态
    if (typeof window !== "undefined") {
      window.addEventListener("online", this.handleOnline);
      window.addEventListener("offline", this.handleOffline);
    }
  }

  // ============ 公共方法 ============

  /** 获取当前连接状态 */
  getState(): ConnectionState {
    return this.state;
  }

  /** 获取连接 ID */
  getConnectionId(): string | null {
    return this.connectionId;
  }

  /** 获取会话 ID */
  getConversationId(): string | null {
    return this.conversationId;
  }

  /** 是否已连接 */
  isConnected(): boolean {
    return this.state === "connected" && this.ws?.readyState === WebSocket.OPEN;
  }

  /** 建立连接 */
  connect(): void {
    if (this.state === "connecting" || this.state === "connected") {
      console.log("[WS] Already connecting or connected");
      return;
    }
    
    this.doConnect();
  }

  /** 断开连接 */
  disconnect(): void {
    this.cleanup();
    this.setState("disconnected");
  }

  /** 发送消息 */
  send(action: string, payload: Record<string, unknown>): string {
    const message = buildMessage(action, payload, this.conversationId ?? undefined);
    
    if (this.isConnected()) {
      this.doSend(message);
    } else {
      // 离线时加入队列
      this.enqueueMessage(message);
    }
    
    return message.id;
  }

  /** 发送原始消息 */
  sendRaw(message: WSMessage): void {
    if (this.isConnected()) {
      this.doSend(message);
    } else {
      this.enqueueMessage(message);
    }
  }

  /** 添加消息监听器 */
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  /** 添加状态变更监听器 */
  onStateChange(handler: StateChangeHandler): () => void {
    this.stateChangeHandlers.add(handler);
    return () => this.stateChangeHandlers.delete(handler);
  }

  /** 添加错误监听器 */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  /** 更新配置 (需要重连生效) */
  updateConfig(config: Partial<WebSocketConfig>): void {
    Object.assign(this.config, config);
  }

  /** 销毁实例 */
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
    
    console.log(`[WS] State: ${prevState} → ${newState}`);
    
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
      console.log("[WS] Connecting to:", url.replace(/token=.*/, "token=***"));
      
      this.ws = new WebSocket(url);
      
      this.ws.onopen = this.handleOpen;
      this.ws.onmessage = this.handleMessage;
      this.ws.onclose = this.handleClose;
      this.ws.onerror = this.handleError;
    } catch (e) {
      console.error("[WS] Failed to create WebSocket:", e);
      this.setState("disconnected");
      this.scheduleReconnect();
    }
  }

  private handleOpen = (): void => {
    console.log("[WS] Connected");
    this.setState("connected");
    this.reconnectAttempts = 0;
    this.lastPongAt = Date.now();
    
    // 启动心跳
    this.startPing();
    
    // 发送队列中的消息
    this.flushMessageQueue();
  };

  private handleMessage = (event: MessageEvent): void => {
    try {
      const message: WSMessage = JSON.parse(event.data);
      
      // 处理系统消息
      if (message.action === "system.connected") {
        this.connectionId = (message.payload as { connection_id?: string }).connection_id ?? null;
        console.log("[WS] Connection ID:", this.connectionId);
      } else if (message.action === "system.pong") {
        this.lastPongAt = Date.now();
        this.clearPongTimeout();
        return; // pong 不需要分发
      }
      
      // 分发给监听器
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
    console.log(`[WS] Closed: code=${event.code}, reason=${event.reason}`);
    
    this.cleanup();
    
    // 非正常关闭时尝试重连
    if (event.code !== 1000 && event.code !== 1001) {
      this.scheduleReconnect();
    } else {
      this.setState("disconnected");
    }
  };

  private handleError = (event: Event): void => {
    const error = new Error("WebSocket error");
    console.error("[WS] Error:", event);
    
    for (const handler of this.errorHandlers) {
      try {
        handler(error);
      } catch (e) {
        console.error("[WS] Error handler error:", e);
      }
    }
  };

  private handleOnline = (): void => {
    console.log("[WS] Network online, attempting reconnect");
    if (this.state === "disconnected" || this.state === "reconnecting") {
      this.reconnectAttempts = 0; // 重置重试次数
      this.connect();
    }
  };

  private handleOffline = (): void => {
    console.log("[WS] Network offline");
    // 网络断开时不立即断开 WS，等待心跳超时
  };

  private cleanup(): void {
    this.stopPing();
    this.clearPongTimeout();
    this.clearReconnectTimer();
    this.connectionId = null;
    
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      
      if (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close(1000, "Client disconnect");
      }
      this.ws = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.log("[WS] Max reconnect attempts reached");
      this.setState("disconnected");
      return;
    }
    
    // 指数退避: 1s, 2s, 4s, 8s, 16s, 30s (max)
    const delay = Math.min(
      this.config.initialReconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.config.maxReconnectDelay
    );
    
    this.reconnectAttempts++;
    this.setState("reconnecting");
    
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.doConnect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  // ============ 心跳相关 ============

  private startPing(): void {
    this.stopPing();
    
    this.pingTimer = setInterval(() => {
      if (this.isConnected()) {
        this.sendPing();
      }
    }, this.config.pingInterval);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private sendPing(): void {
    const message = buildMessage("system.ping", {}, this.conversationId ?? undefined);
    this.doSend(message);
    
    // 设置 pong 超时
    this.pongTimer = setTimeout(() => {
      console.log("[WS] Pong timeout, closing connection");
      this.ws?.close(4002, "Pong timeout");
    }, this.config.pongTimeout);
  }

  private clearPongTimeout(): void {
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  // ============ 消息队列 ============

  private enqueueMessage(message: WSMessage): void {
    if (this.messageQueue.length >= this.maxQueueSize) {
      // 移除最旧的消息
      this.messageQueue.shift();
    }
    this.messageQueue.push(message);
    console.log(`[WS] Message queued (queue size: ${this.messageQueue.length})`);
  }

  private flushMessageQueue(): void {
    if (this.messageQueue.length === 0) return;
    
    console.log(`[WS] Flushing ${this.messageQueue.length} queued messages`);
    
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!;
      this.doSend(message);
    }
  }

  private doSend(message: WSMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return false;
    }
    
    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (e) {
      console.error("[WS] Send error:", e);
      return false;
    }
  }
}

// ============ 导出工厂函数 ============

/**
 * 获取默认 WebSocket 基础 URL
 */
function getDefaultWebSocketBaseUrl(): string {
  if (typeof window === "undefined") return "ws://127.0.0.1:8000";
  
  // 优先使用环境变量
  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl) return envUrl;
  
  // 开发环境直连后端（Next.js rewrites 不支持 WebSocket）
  if (process.env.NODE_ENV === "development") {
    return "ws://127.0.0.1:8000";
  }
  
  // 生产环境使用同域（需要反向代理支持）
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

/**
 * 创建用户端 WebSocket 管理器
 */
export function createUserWebSocketManager(
  baseUrl: string,
  conversationId: string,
  userId: string,
  options?: Partial<Omit<WebSocketConfig, "baseUrl" | "endpoint" | "token">>
): WebSocketManager {
  const effectiveBaseUrl = baseUrl || getDefaultWebSocketBaseUrl();
  return new WebSocketManager({
    baseUrl: effectiveBaseUrl,
    endpoint: `/ws/user/${conversationId}`,
    token: `user_${userId}`,
    ...options,
  });
}

/**
 * 创建客服端 WebSocket 管理器
 */
export function createAgentWebSocketManager(
  baseUrl: string,
  conversationId: string,
  agentId: string,
  options?: Partial<Omit<WebSocketConfig, "baseUrl" | "endpoint" | "token">>
): WebSocketManager {
  const effectiveBaseUrl = baseUrl || getDefaultWebSocketBaseUrl();
  return new WebSocketManager({
    baseUrl: effectiveBaseUrl,
    endpoint: `/ws/agent/${conversationId}`,
    token: `agent_${agentId}`,
    ...options,
  });
}

/**
 * 创建客服工作台全局队列 WebSocket 管理器
 */
export function createSupportQueueWebSocketManager(
  baseUrl: string,
  agentId: string,
  options?: Partial<Omit<WebSocketConfig, "baseUrl" | "endpoint" | "token">>
): WebSocketManager {
  const effectiveBaseUrl = baseUrl || getDefaultWebSocketBaseUrl();
  return new WebSocketManager({
    baseUrl: effectiveBaseUrl,
    endpoint: "/ws/agent-queue",
    token: `agent_${agentId}`,
    ...options,
  });
}
