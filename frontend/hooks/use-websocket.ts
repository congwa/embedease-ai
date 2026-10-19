/**
 * 统一的 WebSocket React Hook
 * 
 * 基于 WebSocketManager 提供 React 组件使用的接口
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  WebSocketManager,
  createUserWebSocketManager,
  createAgentWebSocketManager,
  type ConnectionState,
  type WSMessage,
} from "@/lib/websocket";
import type {
  SupportMessage,
  ConversationState,
  ConnectedPayload,
  ServerMessagePayload,
  TypingPayload,
  HandoffStartedPayload,
  UserPresencePayload,
  AgentPresencePayload,
  ReadReceiptPayload,
  MessageWithdrawnPayload,
  MessageEditedPayload,
  MessagesDeletedPayload,
  ReviewUpdatedPayload,
  TicketUpdatedPayload,
} from "@/types/websocket";
import type { ImageAttachment } from "@/types/chat";

// ============ 公共配置 ============

function getWebSocketBaseUrl(): string {
  if (typeof window === "undefined") return "";
  
  // 优先使用环境变量
  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl) return envUrl;
  
  // Next.js rewrites 不支持 WebSocket，需要直连后端
  // 开发环境默认使用本地后端
  if (process.env.NODE_ENV === "development") {
    return "ws://127.0.0.1:8000";
  }
  
  // 生产环境尝试使用同域 WebSocket（需要 nginx 等反向代理支持）
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

/**
 * 合并会话状态推送
 *
 * 把 system.connected / server.conversation_state / ticket / review 更新统一收敛成前端状态结构。
 */
function mergeConversationState(
  prev: ConversationState,
  next: Partial<ConversationState>
): ConversationState {
  return {
    ...prev,
    ...next,
    current_ticket:
      next.current_ticket !== undefined ? next.current_ticket : prev.current_ticket,
    review_summary:
      next.review_summary !== undefined ? next.review_summary : prev.review_summary,
    recent_tasks:
      next.recent_tasks !== undefined ? next.recent_tasks : prev.recent_tasks,
    secondary_issues:
      next.secondary_issues !== undefined ? next.secondary_issues : prev.secondary_issues,
    handoff_summary:
      next.handoff_summary !== undefined ? next.handoff_summary : prev.handoff_summary,
  };
}

// ============ 用户端 Hook ============

export interface UseUserWebSocketOptions {
  conversationId: string | null;
  userId: string | null;
  wsBaseUrl?: string;
  enabled?: boolean;
  onMessage?: (message: SupportMessage) => void;
  onStateChange?: (state: ConversationState) => void;
  onReadReceipt?: (payload: ReadReceiptPayload) => void;
  onMessageWithdrawn?: (payload: MessageWithdrawnPayload) => void;
  onMessageEdited?: (payload: MessageEditedPayload) => void;
  onMessagesDeleted?: (payload: MessagesDeletedPayload) => void;
}

export interface UseUserWebSocketReturn {
  /** 连接状态 */
  connectionState: ConnectionState;
  /** 是否已连接 */
  isConnected: boolean;
  /** 连接 ID */
  connectionId: string | null;
  /** 会话状态 */
  conversationState: ConversationState;
  /** 客服是否正在输入 */
  agentTyping: boolean;
  /** 发送消息 */
  sendMessage: (content: string) => void;
  /** 设置输入状态 */
  setTyping: (isTyping: boolean) => void;
  /** 请求人工客服 */
  requestHandoff: (reason?: string) => void;
  /** 标记已读 */
  markAsRead: (messageIds: string[]) => void;
  /** 手动重连 */
  reconnect: () => void;
}

const DEFAULT_CONVERSATION_STATE: ConversationState = {
  conversation_mode: "ai",
  handoff_state: "ai",
  user_online: true,
  agent_online: false,
};

export function useUserWebSocket({
  conversationId,
  userId,
  wsBaseUrl,
  enabled = true,
  onMessage,
  onStateChange,
  onReadReceipt,
  onMessageWithdrawn,
  onMessageEdited,
  onMessagesDeleted,
}: UseUserWebSocketOptions): UseUserWebSocketReturn {
  const managerRef = useRef<WebSocketManager | null>(null);
  
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [conversationState, setConversationState] = useState<ConversationState>(DEFAULT_CONVERSATION_STATE);
  const [agentTyping, setAgentTyping] = useState(false);

  // 使用 ref 存储回调以避免重复创建 manager
  const callbacksRef = useRef({
    onMessage,
    onStateChange,
    onReadReceipt,
    onMessageWithdrawn,
    onMessageEdited,
    onMessagesDeleted,
  });
  
  useEffect(() => {
    callbacksRef.current = {
      onMessage,
      onStateChange,
      onReadReceipt,
      onMessageWithdrawn,
      onMessageEdited,
      onMessagesDeleted,
    };
  }, [onMessage, onStateChange, onReadReceipt, onMessageWithdrawn, onMessageEdited, onMessagesDeleted]);

  // 消息处理器
  const handleMessage = useCallback((msg: WSMessage) => {
    const callbacks = callbacksRef.current;
    
    switch (msg.action) {
      case "system.connected": {
        const payload = msg.payload as unknown as ConnectedPayload;
        setConnectionId(payload.connection_id);
        const newState: ConversationState = {
          conversation_mode: (payload.conversation_mode as ConversationState["conversation_mode"]) ?? "ai",
          handoff_state: payload.handoff_state as "ai" | "pending" | "human",
          handoff_reason: null,
          user_online: true,
          agent_online: payload.peer_online,
          peer_last_online_at: payload.peer_last_online_at ?? undefined,
          unread_count: payload.unread_count,
          current_ticket: payload.current_ticket ?? null,
          review_summary: payload.review_summary ?? null,
          recent_tasks: payload.recent_tasks ?? [],
          secondary_issues: payload.secondary_issues ?? [],
          handoff_summary: payload.handoff_summary ?? null,
        };
        setConversationState(newState);
        // 同步状态到 Store
        callbacks.onStateChange?.(newState);
        break;
      }

      case "system.ack":
      case "system.error":
        if (msg.action === "system.error") {
          console.error("[UserWS] Server error:", msg.payload);
        }
        break;

      case "server.message": {
        const payload = msg.payload as unknown as ServerMessagePayload;
        callbacks.onMessage?.({
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
        const payload = msg.payload as unknown as TypingPayload;
        if (payload.role === "agent") {
          setAgentTyping(payload.is_typing);
        }
        break;
      }

      case "server.handoff_started": {
        const payload = msg.payload as unknown as HandoffStartedPayload;
        setConversationState((prev) => {
          const newState = mergeConversationState(prev, {
            conversation_mode: "human",
            handoff_state: "human",
            handoff_reason: payload.reason ?? null,
            operator: payload.operator,
            agent_online: true,
          });
          callbacks.onStateChange?.(newState);
          return newState;
        });
        break;
      }

      case "server.handoff_ended": {
        setConversationState((prev) => {
          const newState = mergeConversationState(prev, {
            conversation_mode: "ai",
            handoff_state: "ai",
            handoff_reason: null,
            operator: undefined,
            agent_online: false,
          });
          callbacks.onStateChange?.(newState);
          return newState;
        });
        setAgentTyping(false);
        break;
      }

      case "server.conversation_state": {
        const payload = msg.payload as unknown as ConversationState;
        setConversationState((prev) => {
          const newState = mergeConversationState(prev, payload);
          callbacks.onStateChange?.(newState);
          return newState;
        });
        break;
      }

      case "server.ticket_updated": {
        const payload = msg.payload as unknown as TicketUpdatedPayload;
        setConversationState((prev) => {
          const newState = mergeConversationState(prev, { current_ticket: payload.ticket });
          callbacks.onStateChange?.(newState);
          return newState;
        });
        break;
      }

      case "server.review_updated": {
        const payload = msg.payload as unknown as ReviewUpdatedPayload;
        setConversationState((prev) => {
          const newState = mergeConversationState(prev, { review_summary: payload.review_summary });
          callbacks.onStateChange?.(newState);
          return newState;
        });
        break;
      }

      case "server.agent_online": {
        const payload = msg.payload as unknown as AgentPresencePayload;
        setConversationState((prev) => {
          const newState = {
            ...prev,
            agent_online: true,
            operator: payload.operator,
            peer_last_online_at: payload.last_online_at,
          };
          callbacks.onStateChange?.(newState);
          return newState;
        });
        break;
      }

      case "server.agent_offline": {
        const payload = msg.payload as unknown as AgentPresencePayload;
        setConversationState((prev) => {
          const newState = {
            ...prev,
            agent_online: false,
            peer_last_online_at: payload.last_online_at,
          };
          callbacks.onStateChange?.(newState);
          return newState;
        });
        setAgentTyping(false);
        break;
      }

      case "server.message_withdrawn": {
        const payload = msg.payload as unknown as MessageWithdrawnPayload;
        callbacks.onMessageWithdrawn?.(payload);
        break;
      }

      case "server.message_edited": {
        const payload = msg.payload as unknown as MessageEditedPayload;
        callbacks.onMessageEdited?.(payload);
        break;
      }

      case "server.messages_deleted": {
        const payload = msg.payload as unknown as MessagesDeletedPayload;
        callbacks.onMessagesDeleted?.(payload);
        break;
      }
    }
  }, []);

  // 创建/销毁 manager
  useEffect(() => {
    // 检查条件
    if (!enabled || !conversationId || !userId) {
      // 清理现有连接
      if (managerRef.current) {
        managerRef.current.destroy();
        managerRef.current = null;
        setConnectionState("disconnected");
        setConnectionId(null);
        setConversationState(DEFAULT_CONVERSATION_STATE);
        setAgentTyping(false);
      }
      return;
    }

    // 如果已有相同配置的 manager，跳过
    if (managerRef.current?.getConversationId() === conversationId) {
      return;
    }

    // 清理旧的 manager
    if (managerRef.current) {
      managerRef.current.destroy();
    }

    // 创建新的 manager
    const baseUrl = wsBaseUrl || getWebSocketBaseUrl();
    const manager = createUserWebSocketManager(baseUrl, conversationId, userId);
    managerRef.current = manager;

    // 设置监听器
    manager.onStateChange((state) => {
      setConnectionState(state);
      if (state === "disconnected") {
        setConnectionId(null);
      }
    });

    manager.onMessage(handleMessage);

    manager.onError((error) => {
      console.error("[UserWS] Error:", error);
    });

    // 连接
    manager.connect();

    return () => {
      manager.destroy();
      managerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, conversationId, userId, wsBaseUrl]);

  // 操作方法
  const sendMessage = useCallback((content: string) => {
    managerRef.current?.send("client.user.send_message", {
      content,
      message_id: crypto.randomUUID?.() || Math.random().toString(36).slice(2),
    });
  }, []);

  const setTyping = useCallback((isTyping: boolean) => {
    managerRef.current?.send("client.user.typing", { is_typing: isTyping });
  }, []);

  const requestHandoff = useCallback((reason?: string) => {
    managerRef.current?.send("client.user.request_handoff", { reason: reason || "" });
  }, []);

  const markAsRead = useCallback((messageIds: string[]) => {
    managerRef.current?.send("client.user.read", { message_ids: messageIds });
  }, []);

  const reconnect = useCallback(() => {
    managerRef.current?.connect();
  }, []);

  return {
    connectionState,
    isConnected: connectionState === "connected",
    connectionId,
    conversationState,
    agentTyping,
    sendMessage,
    setTyping,
    requestHandoff,
    markAsRead,
    reconnect,
  };
}

// ============ 客服端 Hook ============

export interface UseSupportWebSocketOptions {
  conversationId: string;
  agentId: string;
  wsBaseUrl?: string;
  enabled?: boolean;
  onMessage?: (message: SupportMessage) => void;
  onStateChange?: (state: ConversationState) => void;
  onReadReceipt?: (payload: ReadReceiptPayload) => void;
  onMessageWithdrawn?: (payload: MessageWithdrawnPayload) => void;
  onMessageEdited?: (payload: MessageEditedPayload) => void;
  onMessagesDeleted?: (payload: MessagesDeletedPayload) => void;
}

export interface UseSupportWebSocketReturn {
  /** 连接状态 */
  connectionState: ConnectionState;
  /** 是否已连接 */
  isConnected: boolean;
  /** 连接 ID */
  connectionId: string | null;
  /** 会话状态 */
  conversationState: ConversationState;
  /** 用户是否正在输入 */
  userTyping: boolean;
  /** 发送消息 */
  sendMessage: (content: string, images?: ImageAttachment[]) => string;
  /** 设置输入状态 */
  setTyping: (isTyping: boolean) => void;
  /** 开始介入 */
  startHandoff: (reason?: string) => void;
  /** 结束介入 */
  endHandoff: (summary?: string) => void;
  /** 标记已读 */
  markAsRead: (messageIds: string[]) => void;
  /** 撤回消息 */
  withdrawMessage: (messageId: string, reason?: string) => void;
  /** 编辑消息 */
  editMessage: (messageId: string, newContent: string, regenerate?: boolean) => void;
  /** 手动重连 */
  reconnect: () => void;
}

export function useSupportWebSocket({
  conversationId,
  agentId,
  wsBaseUrl,
  enabled = true,
  onMessage,
  onStateChange,
  onReadReceipt,
  onMessageWithdrawn,
  onMessageEdited,
  onMessagesDeleted,
}: UseSupportWebSocketOptions): UseSupportWebSocketReturn {
  const managerRef = useRef<WebSocketManager | null>(null);
  
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [conversationState, setConversationState] = useState<ConversationState>({
    conversation_mode: "ai",
    handoff_state: "ai",
    user_online: false,
    agent_online: true,
  });
  const [userTyping, setUserTyping] = useState(false);

  // 使用 ref 存储回调
  const callbacksRef = useRef({
    onMessage,
    onStateChange,
    onReadReceipt,
    onMessageWithdrawn,
    onMessageEdited,
    onMessagesDeleted,
  });
  
  useEffect(() => {
    callbacksRef.current = {
      onMessage,
      onStateChange,
      onReadReceipt,
      onMessageWithdrawn,
      onMessageEdited,
      onMessagesDeleted,
    };
  }, [onMessage, onStateChange, onReadReceipt, onMessageWithdrawn, onMessageEdited, onMessagesDeleted]);

  // WebSocket callbacks must run outside React's state updater: the callback updates the shared support store.
  // Keep the latest snapshot in a ref so consecutive events merge in order, even before the next render.
  const supportStateRef = useRef(conversationState);
  const updateSupportState = useCallback((update: (previous: ConversationState) => ConversationState) => {
    const next = update(supportStateRef.current);
    supportStateRef.current = next;
    setConversationState(next);
    callbacksRef.current.onStateChange?.(next);
  }, []);

  // 消息处理器
  const handleMessage = useCallback((msg: WSMessage) => {
    const callbacks = callbacksRef.current;
    
    switch (msg.action) {
      case "system.connected": {
        const payload = msg.payload as unknown as ConnectedPayload;
        setConnectionId(payload.connection_id);
        const newState: ConversationState = {
          conversation_mode: (payload.conversation_mode as ConversationState["conversation_mode"]) ?? "ai",
          handoff_state: payload.handoff_state as "ai" | "pending" | "human",
          handoff_reason: null,
          agent_online: true,
          user_online: payload.peer_online,
          peer_last_online_at: payload.peer_last_online_at ?? undefined,
          unread_count: payload.unread_count,
          current_ticket: payload.current_ticket ?? null,
          review_summary: payload.review_summary ?? null,
          recent_tasks: payload.recent_tasks ?? [],
          secondary_issues: payload.secondary_issues ?? [],
          handoff_summary: payload.handoff_summary ?? null,
        };
        supportStateRef.current = newState;
        setConversationState(newState);
        // 同步状态到 Store
        callbacks.onStateChange?.(newState);
        break;
      }

      case "system.ack":
      case "system.error":
        if (msg.action === "system.error") {
          console.error("[AgentWS] Server error:", msg.payload);
        }
        break;

      case "server.message": {
        const payload = msg.payload as unknown as ServerMessagePayload;
        callbacks.onMessage?.({
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
        const payload = msg.payload as unknown as TypingPayload;
        if (payload.role === "user") {
          setUserTyping(payload.is_typing);
        }
        break;
      }

      case "server.handoff_started": {
        const payload = msg.payload as unknown as HandoffStartedPayload;
        updateSupportState((prev) => {
          const newState = mergeConversationState(prev, {
            conversation_mode: "human",
            handoff_state: "human",
            handoff_reason: payload.reason ?? null,
            operator: payload.operator,
          });
          return newState;
        });
        break;
      }

      case "server.handoff_ended": {
        updateSupportState((prev) => {
          const newState = mergeConversationState(prev, {
            conversation_mode: "ai",
            handoff_state: "ai",
            handoff_reason: null,
            operator: undefined,
          });
          return newState;
        });
        break;
      }

      case "server.conversation_state": {
        const payload = msg.payload as unknown as ConversationState;
        updateSupportState((prev) => {
          const newState = mergeConversationState(prev, payload);
          return newState;
        });
        break;
      }

      case "server.ticket_updated": {
        const payload = msg.payload as unknown as TicketUpdatedPayload;
        updateSupportState((prev) => {
          const newState = mergeConversationState(prev, { current_ticket: payload.ticket });
          return newState;
        });
        break;
      }

      case "server.review_updated": {
        const payload = msg.payload as unknown as ReviewUpdatedPayload;
        updateSupportState((prev) => {
          const newState = mergeConversationState(prev, { review_summary: payload.review_summary });
          return newState;
        });
        break;
      }

      case "server.user_online": {
        const payload = msg.payload as unknown as UserPresencePayload;
        updateSupportState((prev) => {
          const newState = {
            ...prev,
            user_online: true,
            peer_last_online_at: payload.last_online_at,
          };
          return newState;
        });
        break;
      }

      case "server.user_offline": {
        const payload = msg.payload as unknown as UserPresencePayload;
        updateSupportState((prev) => {
          const newState = {
            ...prev,
            user_online: false,
            peer_last_online_at: payload.last_online_at,
          };
          return newState;
        });
        setUserTyping(false);
        break;
      }

      case "server.message_withdrawn": {
        const payload = msg.payload as unknown as MessageWithdrawnPayload;
        callbacks.onMessageWithdrawn?.(payload);
        break;
      }

      case "server.message_edited": {
        const payload = msg.payload as unknown as MessageEditedPayload;
        callbacks.onMessageEdited?.(payload);
        break;
      }

      case "server.messages_deleted": {
        const payload = msg.payload as unknown as MessagesDeletedPayload;
        callbacks.onMessagesDeleted?.(payload);
        break;
      }
    }
  }, [updateSupportState]);

  // 创建/销毁 manager
  useEffect(() => {
    if (!enabled || !conversationId || !agentId) {
      if (managerRef.current) {
        managerRef.current.destroy();
        managerRef.current = null;
        setConnectionState("disconnected");
        setConnectionId(null);
      }
      return;
    }

    if (managerRef.current?.getConversationId() === conversationId) {
      return;
    }

    if (managerRef.current) {
      managerRef.current.destroy();
    }

    const baseUrl = wsBaseUrl || getWebSocketBaseUrl();
    const manager = createAgentWebSocketManager(baseUrl, conversationId, agentId);
    managerRef.current = manager;

    manager.onStateChange((state) => {
      setConnectionState(state);
      if (state === "disconnected") {
        setConnectionId(null);
      }
    });

    manager.onMessage(handleMessage);

    manager.onError((error) => {
      console.error("[AgentWS] Error:", error);
    });

    manager.connect();

    return () => {
      manager.destroy();
      managerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, conversationId, agentId, wsBaseUrl]);

  // 操作方法
  /**
   * 发送人工客服消息并返回本地可复用的消息 ID。
   *
   * 这个方法服务于客服工作台乐观渲染，让本地消息和服务端落库消息共用同一个标识，
   * 避免消息送达后在界面上出现重复气泡。
   */
  const sendMessage = useCallback((content: string, images?: ImageAttachment[]) => {
    const messageId = crypto.randomUUID?.() || Math.random().toString(36).slice(2);
    const payload: Record<string, unknown> = {
      content,
      message_id: messageId,
    };
    if (images && images.length > 0) {
      payload.images = images;
    }
    managerRef.current?.send("client.agent.send_message", payload);
    return messageId;
  }, []);

  const setTyping = useCallback((isTyping: boolean) => {
    managerRef.current?.send("client.agent.typing", { is_typing: isTyping });
  }, []);

  const startHandoff = useCallback((reason?: string) => {
    managerRef.current?.send("client.agent.start_handoff", { reason: reason || "" });
  }, []);

  const endHandoff = useCallback((summary?: string) => {
    managerRef.current?.send("client.agent.end_handoff", { summary: summary || "" });
  }, []);

  const markAsRead = useCallback((messageIds: string[]) => {
    managerRef.current?.send("client.agent.read", { message_ids: messageIds });
  }, []);

  const withdrawMessage = useCallback((messageId: string, reason?: string) => {
    managerRef.current?.send("client.agent.withdraw_message", {
      message_id: messageId,
      reason: reason || "",
    });
  }, []);

  const editMessage = useCallback((messageId: string, newContent: string, regenerate = true) => {
    managerRef.current?.send("client.agent.edit_message", {
      message_id: messageId,
      new_content: newContent,
      regenerate,
    });
  }, []);

  const reconnect = useCallback(() => {
    managerRef.current?.connect();
  }, []);

  return {
    connectionState,
    isConnected: connectionState === "connected",
    connectionId,
    conversationState,
    userTyping,
    sendMessage,
    setTyping,
    startHandoff,
    endHandoff,
    markAsRead,
    withdrawMessage,
    editMessage,
    reconnect,
  };
}
