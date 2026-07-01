/**
 * Embed 版本的 WebSocket Hook
 * 
 * 基于统一的 WebSocketManager，为 Embed 组件提供独立的实现
 * 避免依赖 @/types 和其他前端模块
 */

import { useCallback, useEffect, useRef, useState } from "react";

// ============ 常量和类型 ============

const WS_PROTOCOL_VERSION = 1;

export type ConnectionState = 
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

export interface SupportMessage {
  id: string;
  role: "user" | "assistant" | "human_agent" | "system";
  content: string;
  created_at: string;
  operator?: string;
  is_delivered?: boolean;
  delivered_at?: string;
  read_at?: string;
  read_by?: string;
  is_withdrawn?: boolean;
  withdrawn_at?: string;
  withdrawn_by?: string;
  is_edited?: boolean;
  edited_at?: string;
  edited_by?: string;
}

export interface ConversationState {
  handoff_state: "ai" | "pending" | "human";
  operator?: string;
  user_online: boolean;
  agent_online: boolean;
  peer_last_online_at?: string;
  unread_count?: number;
}

export interface ReadReceiptPayload {
  role: string;
  message_ids: string[];
  read_at: string;
  read_by: string;
}

interface WSMessage {
  v: number;
  id: string;
  ts: number;
  action: string;
  payload: Record<string, unknown>;
  conversation_id?: string;
}

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

// ============ Hook 配置 ============

interface UseEmbedWebSocketOptions {
  conversationId: string | null;
  userId: string | null;
  wsBaseUrl?: string;
  enabled?: boolean;
  onMessage?: (message: SupportMessage) => void;
  onStateChange?: (state: ConversationState) => void;
  onReadReceipt?: (payload: ReadReceiptPayload) => void;
}

interface UseEmbedWebSocketReturn {
  connectionState: ConnectionState;
  isConnected: boolean;
  conversationState: ConversationState;
  agentTyping: boolean;
  sendMessage: (content: string) => void;
  setTyping: (isTyping: boolean) => void;
  requestHandoff: (reason?: string) => void;
}

// ============ Hook 实现 ============

const DEFAULT_STATE: ConversationState = {
  handoff_state: "ai",
  user_online: true,
  agent_online: false,
};

export function useEmbedWebSocket({
  conversationId,
  userId,
  wsBaseUrl,
  enabled = true,
  onMessage,
  onStateChange,
  onReadReceipt,
}: UseEmbedWebSocketOptions): UseEmbedWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const connectRef = useRef<(() => void) | null>(null);

  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [conversationState, setConversationState] = useState<ConversationState>(DEFAULT_STATE);
  const [agentTyping, setAgentTyping] = useState(false);

  // 使用 ref 存储回调
  const callbacksRef = useRef({ onMessage, onStateChange, onReadReceipt });
  useEffect(() => {
    callbacksRef.current = { onMessage, onStateChange, onReadReceipt };
  }, [onMessage, onStateChange, onReadReceipt]);

  // 发送消息
  const send = useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  // 消息处理
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg: WSMessage = JSON.parse(event.data);
      const callbacks = callbacksRef.current;

      switch (msg.action) {
        case "system.connected": {
          const payload = msg.payload as {
            connection_id: string;
            handoff_state: string;
            peer_online: boolean;
            peer_last_online_at: string | null;
            unread_count: number;
          };
          setConversationState((prev) => ({
            ...prev,
            handoff_state: payload.handoff_state as "ai" | "pending" | "human",
            user_online: true,
            agent_online: payload.peer_online,
            peer_last_online_at: payload.peer_last_online_at ?? undefined,
            unread_count: payload.unread_count,
          }));
          break;
        }

        case "system.pong":
        case "system.ack":
          break;

        case "system.error":
          console.error("[EmbedWS] Error:", msg.payload);
          break;

        case "server.message": {
          const payload = msg.payload as {
            message_id: string;
            role: "user" | "assistant" | "human_agent" | "system";
            content: string;
            created_at: string;
            operator?: string;
            is_delivered?: boolean;
            delivered_at?: string;
            read_at?: string;
            read_by?: string;
            is_withdrawn?: boolean;
            withdrawn_at?: string;
            withdrawn_by?: string;
            is_edited?: boolean;
            edited_at?: string;
            edited_by?: string;
          };
          callbacks.onMessage?.({
            id: payload.message_id,
            role: payload.role,
            content: payload.content,
            created_at: payload.created_at,
            operator: payload.operator,
            is_delivered: payload.is_delivered,
            delivered_at: payload.delivered_at,
            read_at: payload.read_at,
            read_by: payload.read_by,
            is_withdrawn: payload.is_withdrawn,
            withdrawn_at: payload.withdrawn_at,
            withdrawn_by: payload.withdrawn_by,
            is_edited: payload.is_edited,
            edited_at: payload.edited_at,
            edited_by: payload.edited_by,
          });
          break;
        }

        case "server.read_receipt": {
          const payload = msg.payload as unknown as ReadReceiptPayload;
          callbacks.onReadReceipt?.(payload);
          break;
        }

        case "server.typing": {
          const payload = msg.payload as { role: string; is_typing: boolean };
          if (payload.role === "agent") {
            setAgentTyping(payload.is_typing);
          }
          break;
        }

        case "server.handoff_started": {
          const payload = msg.payload as { operator: string };
          setConversationState((prev) => {
            const newState: ConversationState = {
              ...prev,
              handoff_state: "human",
              operator: payload.operator,
              agent_online: true,
            };
            callbacks.onStateChange?.(newState);
            return newState;
          });
          break;
        }

        case "server.handoff_ended": {
          setConversationState((prev) => {
            const newState: ConversationState = {
              ...prev,
              handoff_state: "ai",
              operator: undefined,
              agent_online: false,
            };
            callbacks.onStateChange?.(newState);
            return newState;
          });
          setAgentTyping(false);
          break;
        }

        case "server.agent_online": {
          const payload = msg.payload as { operator: string; last_online_at?: string };
          setConversationState((prev) => ({
            ...prev,
            agent_online: true,
            operator: payload.operator,
            peer_last_online_at: payload.last_online_at,
          }));
          break;
        }

        case "server.agent_offline": {
          const payload = msg.payload as { last_online_at?: string };
          setConversationState((prev) => ({
            ...prev,
            agent_online: false,
            peer_last_online_at: payload.last_online_at,
          }));
          setAgentTyping(false);
          break;
        }
      }
    } catch (e) {
      console.error("[EmbedWS] Parse error:", e);
    }
  }, []);

  // 连接函数
  const connect = useCallback(() => {
    if (!conversationId || !userId || !enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    let baseUrl = wsBaseUrl;
    if (!baseUrl) {
      // Next.js rewrites 不支持 WebSocket，需要直连后端
      if (process.env.NODE_ENV === "development") {
        baseUrl = "ws://127.0.0.1:8000";
      } else if (typeof window !== "undefined") {
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        baseUrl = `${protocol}//${window.location.host}`;
      }
    }
    if (!baseUrl) return;

    const url = `${baseUrl}/ws/user/${conversationId}?token=user_${userId}`;

    try {
      setConnectionState("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnectionState("connected");
        reconnectAttemptsRef.current = 0;
        console.log("[EmbedWS] Connected");

        // 心跳
        pingIntervalRef.current = setInterval(() => {
          send(buildMessage("system.ping", {}, conversationId));
        }, 30000);
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        setConnectionState("disconnected");
        console.log(`[EmbedWS] Closed: ${event.code}`);

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // 非正常关闭时重连（指数退避）
        if (event.code !== 1000 && event.code !== 1001 && enabled) {
          const attempts = reconnectAttemptsRef.current;
          if (attempts < 10) {
            const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
            reconnectAttemptsRef.current++;
            setConnectionState("reconnecting");
            console.log(`[EmbedWS] Reconnecting in ${delay}ms (attempt ${attempts + 1})`);
            reconnectTimeoutRef.current = setTimeout(() => {
              connectRef.current?.();
            }, delay);
          }
        }
      };

      ws.onerror = (error) => {
        console.error("[EmbedWS] Error:", error);
      };
    } catch (e) {
      console.error("[EmbedWS] Connect failed:", e);
      setConnectionState("disconnected");
    }
  }, [conversationId, userId, wsBaseUrl, enabled, send, handleMessage]);

  /**
   * 持有最新 connect 引用，供断线重连定时器调用。
   *
   * 这个副作用服务于 Embed 场景下的指数退避重连，避免定时器闭包持有过期 connect，
   * 同时规避 React Hook 规则对“定义前引用”的限制。
   */
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // 断开函数
  const disconnect = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "Client disconnect");
      wsRef.current = null;
    }
    setConnectionState("disconnected");
    reconnectAttemptsRef.current = 0;
  }, []);

  // 生命周期
  useEffect(() => {
    if (enabled && conversationId && userId) {
      const connectTimer = setTimeout(() => {
        connectRef.current?.();
      }, 0);
      return () => {
        clearTimeout(connectTimer);
        disconnect();
      };
    } else {
      const disconnectTimer = setTimeout(() => {
        disconnect();
      }, 0);
      return () => {
        clearTimeout(disconnectTimer);
      };
    }
  }, [conversationId, userId, enabled, connect, disconnect]);

  // 操作方法
  const sendMessage = useCallback(
    (content: string) => {
      if (!conversationId) return;
      send(buildMessage("client.user.send_message", { content, message_id: generateId() }, conversationId));
    },
    [send, conversationId]
  );

  const setTyping = useCallback(
    (isTyping: boolean) => {
      if (!conversationId) return;
      send(buildMessage("client.user.typing", { is_typing: isTyping }, conversationId));
    },
    [send, conversationId]
  );

  const requestHandoff = useCallback(
    (reason?: string) => {
      if (!conversationId) return;
      send(buildMessage("client.user.request_handoff", { reason: reason || "" }, conversationId));
    },
    [send, conversationId]
  );

  return {
    connectionState,
    isConnected: connectionState === "connected",
    conversationState,
    agentTyping,
    sendMessage,
    setTyping,
    requestHandoff,
  };
}
