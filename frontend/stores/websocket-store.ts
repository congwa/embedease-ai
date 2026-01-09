/**
 * WebSocket 连接状态管理 Store
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { ConversationState, SupportMessage } from "@/types/websocket";
import { WS_PROTOCOL_VERSION } from "@/types/websocket";
import { useUserStore } from "./user-store";
import { useConversationStore } from "./conversation-store";
import { useChatStore } from "./chat-store";

interface WebSocketState {
  isConnected: boolean;
  connectionId: string | null;
  conversationState: ConversationState;
  agentTyping: boolean;

  ws: WebSocket | null;
  pingInterval: ReturnType<typeof setInterval> | null;
  reconnectTimeout: ReturnType<typeof setTimeout> | null;

  connect: () => void;
  disconnect: () => void;
  sendMessage: (content: string) => void;
  setTyping: (isTyping: boolean) => void;
  requestHandoff: (reason?: string) => void;
  markAsRead: (messageIds: string[]) => void;

  _handleMessage: (event: MessageEvent) => void;
  _send: (message: object) => void;
}

const DEFAULT_CONVERSATION_STATE: ConversationState = {
  handoff_state: "ai",
  user_online: true,
  agent_online: false,
};

function generateId(): string {
  return crypto.randomUUID?.() || Math.random().toString(36).slice(2);
}

function buildMessage(action: string, payload: object, conversationId?: string) {
  return {
    v: WS_PROTOCOL_VERSION,
    id: generateId(),
    ts: Date.now(),
    action,
    payload,
    conversation_id: conversationId,
  };
}

export const useWebSocketStore = create<WebSocketState>()(
  subscribeWithSelector((set, get) => ({
    isConnected: false,
    connectionId: null,
    conversationState: DEFAULT_CONVERSATION_STATE,
    agentTyping: false,
    ws: null,
    pingInterval: null,
    reconnectTimeout: null,

    connect: () => {
      const userId = useUserStore.getState().userId;
      const conversationId = useConversationStore.getState().currentConversationId;

      if (!userId || !conversationId) return;
      if (get().ws?.readyState === WebSocket.OPEN) return;

      const protocol = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = typeof window !== "undefined" ? window.location.host : "localhost:3000";
      const envWsUrl = typeof window !== "undefined" ? (window as unknown as { __ENV__?: { NEXT_PUBLIC_WS_URL?: string } }).__ENV__?.NEXT_PUBLIC_WS_URL : undefined;
      const wsUrl = envWsUrl || `${protocol}//${host}`;
      const url = `${wsUrl}/ws/user/${conversationId}?token=user_${userId}`;

      try {
        const ws = new WebSocket(url);
        set({ ws });

        ws.onopen = () => {
          set({ isConnected: true });
          console.log("[WebSocketStore] Connected");

          const pingInterval = setInterval(() => {
            const currentConvId = useConversationStore.getState().currentConversationId;
            get()._send(buildMessage("system.ping", {}, currentConvId || undefined));
          }, 30000);
          set({ pingInterval });
        };

        ws.onmessage = get()._handleMessage;

        ws.onclose = () => {
          set({ isConnected: false, connectionId: null });
          console.log("[WebSocketStore] Disconnected");

          const { pingInterval } = get();
          if (pingInterval) {
            clearInterval(pingInterval);
            set({ pingInterval: null });
          }

          const currentConvId = useConversationStore.getState().currentConversationId;
          const currentUserId = useUserStore.getState().userId;
          if (currentConvId && currentUserId) {
            const reconnectTimeout = setTimeout(() => {
              console.log("[WebSocketStore] Reconnecting...");
              get().connect();
            }, 3000);
            set({ reconnectTimeout });
          }
        };

        ws.onerror = (error) => {
          console.error("[WebSocketStore] Error:", error);
        };
      } catch (e) {
        console.error("[WebSocketStore] Failed to connect:", e);
      }
    },

    disconnect: () => {
      const { ws, pingInterval, reconnectTimeout } = get();

      if (pingInterval) {
        clearInterval(pingInterval);
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        ws.close();
      }

      set({
        ws: null,
        pingInterval: null,
        reconnectTimeout: null,
        isConnected: false,
        connectionId: null,
        conversationState: DEFAULT_CONVERSATION_STATE,
        agentTyping: false,
      });
    },

    _send: (message: object) => {
      const { ws } = get();
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(message));
      }
    },

    _handleMessage: (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data);

        switch (msg.action) {
          case "system.connected": {
            set({
              connectionId: msg.payload.connection_id,
              conversationState: {
                ...get().conversationState,
                handoff_state: msg.payload.handoff_state,
                user_online: true,
                agent_online: msg.payload.peer_online,
              },
            });
            break;
          }

          case "server.message": {
            if (msg.payload.role === "human_agent") {
              // 可以在这里添加客服消息到 timeline
              console.log("[WebSocketStore] 收到客服消息:", msg.payload);
            }
            break;
          }

          case "server.typing": {
            if (msg.payload.role === "agent") {
              set({ agentTyping: msg.payload.is_typing });
            }
            break;
          }

          case "server.handoff_started": {
            const newState: ConversationState = {
              ...get().conversationState,
              handoff_state: "human",
              operator: msg.payload.operator,
              agent_online: true,
            };
            set({ conversationState: newState });
            useChatStore.getState().setHumanMode(true);
            break;
          }

          case "server.handoff_ended": {
            const newState: ConversationState = {
              ...get().conversationState,
              handoff_state: "ai",
              operator: undefined,
              agent_online: false,
            };
            set({ conversationState: newState, agentTyping: false });
            useChatStore.getState().setHumanMode(false);
            break;
          }

          case "server.agent_online": {
            set((state) => ({
              conversationState: {
                ...state.conversationState,
                agent_online: true,
                operator: msg.payload.operator,
              },
            }));
            break;
          }

          case "server.agent_offline": {
            set((state) => ({
              conversationState: {
                ...state.conversationState,
                agent_online: false,
              },
              agentTyping: false,
            }));
            break;
          }

          case "system.pong":
          case "system.ack":
            break;

          case "system.error":
            console.error("[WebSocketStore] Server error:", msg.payload);
            break;

          default:
            console.log("[WebSocketStore] Unknown action:", msg.action);
        }
      } catch (e) {
        console.error("[WebSocketStore] Failed to parse message:", e);
      }
    },

    sendMessage: (content: string) => {
      const conversationId = useConversationStore.getState().currentConversationId;
      if (!conversationId) return;
      get()._send(
        buildMessage("client.user.send_message", { content, message_id: generateId() }, conversationId)
      );
    },

    setTyping: (isTyping: boolean) => {
      const conversationId = useConversationStore.getState().currentConversationId;
      if (!conversationId) return;
      get()._send(buildMessage("client.user.typing", { is_typing: isTyping }, conversationId));
    },

    requestHandoff: (reason?: string) => {
      const conversationId = useConversationStore.getState().currentConversationId;
      if (!conversationId) return;
      get()._send(buildMessage("client.user.request_handoff", { reason: reason || "" }, conversationId));
    },

    markAsRead: (messageIds: string[]) => {
      const conversationId = useConversationStore.getState().currentConversationId;
      if (!conversationId) return;
      get()._send(buildMessage("client.user.read", { message_ids: messageIds }, conversationId));
    },
  }))
);

// 订阅会话变化，自动连接/断开 WebSocket
let prevWsConversationId: string | null = null;
useConversationStore.subscribe((state) => {
  const conversationId = state.currentConversationId;
  if (conversationId !== prevWsConversationId) {
    prevWsConversationId = conversationId;
    useWebSocketStore.getState().disconnect();
    if (conversationId) {
      setTimeout(() => {
        useWebSocketStore.getState().connect();
      }, 100);
    }
  }
});
