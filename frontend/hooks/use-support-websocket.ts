// 客服端 WebSocket Hook

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  WSMessage,
  WSAction,
  SupportMessage,
  ConversationState,
  ConnectedPayload,
  ServerMessagePayload,
  TypingPayload,
  HandoffStartedPayload,
  HandoffEndedPayload,
  UserPresencePayload,
  ConversationStatePayload,
  ReadReceiptPayload,
} from "@/types/websocket";
import { WS_PROTOCOL_VERSION } from "@/types/websocket";
import type { ImageAttachment } from "@/types/chat";

interface UseSupportWebSocketOptions {
  conversationId: string;
  agentId: string;
  onMessage?: (message: SupportMessage) => void;
  onStateChange?: (state: ConversationState) => void;
  onReadReceipt?: (payload: ReadReceiptPayload) => void;
}

interface UseSupportWebSocketReturn {
  isConnected: boolean;
  connectionId: string | null;
  conversationState: ConversationState;
  userTyping: boolean;
  sendMessage: (content: string, images?: ImageAttachment[]) => void;
  setTyping: (isTyping: boolean) => void;
  startHandoff: (reason?: string) => void;
  endHandoff: (summary?: string) => void;
  markAsRead: (messageIds: string[]) => void;
}

function generateId(): string {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
}

function buildMessage(
  action: WSAction,
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

export function useSupportWebSocket({
  conversationId,
  agentId,
  onMessage,
  onStateChange,
  onReadReceipt,
}: UseSupportWebSocketOptions): UseSupportWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const conversationStateRef = useRef<ConversationState>({
    handoff_state: "ai",
    user_online: false,
    agent_online: false,
  });
  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [conversationState, setConversationState] = useState<ConversationState>(
    conversationStateRef.current
  );
  const [userTyping, setUserTyping] = useState(false);

  useEffect(() => {
    conversationStateRef.current = conversationState;
  }, [conversationState]);

  // 发送消息
  const send = useCallback((message: WSMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  // 处理收到的消息
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const msg: WSMessage = JSON.parse(event.data);
      const currentState = conversationStateRef.current;

      switch (msg.action) {
        case "system.connected": {
          const payload = msg.payload as unknown as ConnectedPayload;
          setConnectionId(payload.connection_id);
          setConversationState((prev) => ({
            ...prev,
            handoff_state: payload.handoff_state as "ai" | "pending" | "human",
            agent_online: true,
            user_online: payload.peer_online,
            peer_last_online_at: payload.peer_last_online_at ?? undefined,
            unread_count: payload.unread_count,
          }));
          break;
        }

        case "system.pong":
          break;
        case "system.ack":
          break;
        case "system.error":
          console.error("WebSocket error:", msg.payload);
          break;

        case "server.message": {
          const payload = msg.payload as unknown as ServerMessagePayload;
          onMessage?.({
            id: payload.message_id,
            role: payload.role,
            content: payload.content,
            created_at: payload.created_at,
            operator: payload.operator,
            images: payload.images,
            is_delivered: payload.is_delivered,
            delivered_at: payload.delivered_at,
            read_at: payload.read_at,
            read_by: payload.read_by,
          });
          break;
        }

        case "server.read_receipt": {
          const payload = msg.payload as unknown as ReadReceiptPayload;
          onReadReceipt?.(payload);
          break;
        }

        case "server.typing": {
          const payload = msg.payload as unknown as TypingPayload;
          if (payload.role === "user") {
            setUserTyping(payload.is_typing);
          }
          break;
        }

        case "server.handoff_started": {
          const payload = msg.payload as unknown as HandoffStartedPayload;
          const newState: ConversationState = {
            ...currentState,
            handoff_state: "human",
            operator: payload.operator,
          };
          setConversationState(newState);
          onStateChange?.(newState);
          break;
        }

        case "server.handoff_ended": {
          const newState: ConversationState = {
            ...currentState,
            handoff_state: "ai",
            operator: undefined,
          };
          setConversationState(newState);
          onStateChange?.(newState);
          break;
        }

        case "server.user_online": {
          const payload = msg.payload as unknown as UserPresencePayload;
          setConversationState((prev) => ({
            ...prev,
            user_online: true,
            peer_last_online_at: payload.last_online_at,
          }));
          break;
        }

        case "server.user_offline": {
          const payload = msg.payload as unknown as UserPresencePayload;
          setConversationState((prev) => ({
            ...prev,
            user_online: false,
            peer_last_online_at: payload.last_online_at,
          }));
          setUserTyping(false);
          break;
        }

        case "server.conversation_state": {
          const payload = msg.payload as unknown as ConversationStatePayload;
          const newState: ConversationState = {
            ...currentState,
            handoff_state: payload.handoff_state as "ai" | "pending" | "human",
            operator: payload.operator,
          };
          setConversationState(newState);
          onStateChange?.(newState);
          break;
        }

        default:
          console.log("Unknown action:", msg.action, msg.payload);
      }
    } catch (e) {
      console.error("Failed to parse WebSocket message:", e);
    }
  }, [onMessage, onStateChange]);

  // 连接 WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${window.location.host}`;
    const url = `${wsUrl}/ws/agent/${conversationId}?token=agent_${agentId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log("WebSocket connected");

      // 启动心跳
      pingIntervalRef.current = setInterval(() => {
        send(buildMessage("system.ping", {}, conversationId));
      }, 30000);
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      setIsConnected(false);
      setConnectionId(null);
      console.log("WebSocket disconnected");

      // 清理心跳
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // 自动重连
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log("Reconnecting...");
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [conversationId, agentId, send, handleMessage]);

  // 初始化连接
  useEffect(() => {
    if (conversationId && agentId) {
      connect();
    }

    return () => {
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [conversationId, agentId, connect]);

  // 发送消息（支持图片）
  const sendMessage = useCallback(
    (content: string, images?: ImageAttachment[]) => {
      const payload: Record<string, unknown> = {
        content,
        message_id: generateId(),
      };
      if (images && images.length > 0) {
        payload.images = images;
      }
      send(buildMessage("client.agent.send_message", payload, conversationId));
    },
    [send, conversationId]
  );

  // 设置输入状态
  const setTyping = useCallback(
    (isTyping: boolean) => {
      send(buildMessage("client.agent.typing", { is_typing: isTyping }, conversationId));
    },
    [send, conversationId]
  );

  // 开始介入
  const startHandoff = useCallback(
    (reason?: string) => {
      send(buildMessage("client.agent.start_handoff", { reason: reason || "" }, conversationId));
    },
    [send, conversationId]
  );

  // 结束介入
  const endHandoff = useCallback(
    (summary?: string) => {
      send(buildMessage("client.agent.end_handoff", { summary: summary || "" }, conversationId));
    },
    [send, conversationId]
  );

  // 标记已读
  const markAsRead = useCallback(
    (messageIds: string[]) => {
      send(buildMessage("client.agent.read", { message_ids: messageIds }, conversationId));
    },
    [send, conversationId]
  );

  return {
    isConnected,
    connectionId,
    conversationState,
    userTyping,
    sendMessage,
    setTyping,
    startHandoff,
    endHandoff,
    markAsRead,
  };
}
