/**
 * useChat Hook
 *
 * 聊天功能完整 Hook，整合 SSE 流式聊天和 Timeline 状态管理
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChatClient,
  createInitialState,
  addUserMessage as sdkAddUserMessage,
  startAssistantTurn as sdkStartAssistantTurn,
  clearTurn as sdkClearTurn,
  endTurn as sdkEndTurn,
  timelineReducer as sdkTimelineReducer,
  historyToTimeline as sdkHistoryToTimeline,
  createUserWebSocketManager,
  type TimelineState,
  type TimelineItem,
  type ChatEvent,
  type ImageAttachment,
  type HistoryMessage,
  type WebSocketManager,
  type WSMessage,
  type ConnectionState,
} from "@embedease/chat-sdk";

export interface UseChatOptions {
  /** API 基础 URL */
  baseUrl: string;

  /** WebSocket 基础 URL（可选，默认自动推断） */
  wsBaseUrl?: string;

  /** 会话 ID */
  conversationId?: string;

  /** 用户 ID */
  userId?: string;

  /** 初始消息列表 */
  initialMessages?: HistoryMessage[];

  /** 事件处理器 */
  onEvent?: (event: ChatEvent) => void;

  /** 错误处理器 */
  onError?: (error: Error) => void;

  /** 消息发送完成回调 */
  onComplete?: () => void;

  /** 是否启用 WebSocket */
  enableWebSocket?: boolean;

  /** WebSocket 消息处理器 */
  onWebSocketMessage?: (message: WSMessage) => void;

  /** 加载历史消息函数 */
  loadHistory?: () => Promise<HistoryMessage[]>;
}

export interface UseChatReturn {
  /** 时间线状态 */
  timeline: TimelineItem[];

  /** 完整状态 */
  state: TimelineState;

  /** 是否正在流式响应 */
  isStreaming: boolean;

  /** 是否正在加载 */
  isLoading: boolean;

  /** 错误信息 */
  error: Error | null;

  /** 发送消息 */
  sendMessage: (content: string, images?: ImageAttachment[]) => Promise<void>;

  /** 中止流 */
  abort: () => void;

  /** 清空消息 */
  clearMessages: () => void;

  /** 从历史消息初始化 */
  initFromHistory: (messages: HistoryMessage[]) => void;

  /** 重新加载历史消息 */
  reload: () => Promise<void>;

  /** 当前 Turn ID */
  currentTurnId: string | null;

  /** 设置状态 */
  setState: (state: TimelineState) => void;

  /** WebSocket 连接状态 */
  wsConnected: boolean;

  /** 发送 WebSocket 消息 */
  wsSendMessage: (action: string, payload: Record<string, unknown>) => void;
}

function getWebSocketBaseUrl(apiBaseUrl: string): string {
  if (typeof window === "undefined") return "";

  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl) return envUrl;

  if (process.env.NODE_ENV === "development") {
    return "ws://127.0.0.1:8000";
  }

  try {
    const url = new URL(apiBaseUrl);
    const protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${url.host}`;
  } catch {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}`;
  }
}

export function useChat(options: UseChatOptions): UseChatReturn {
  const {
    baseUrl,
    wsBaseUrl,
    conversationId,
    userId,
    initialMessages,
    onEvent,
    onError,
    onComplete,
    enableWebSocket = false,
    onWebSocketMessage,
    loadHistory,
  } = options;

  const [state, setStateInternal] = useState<TimelineState>(() =>
    initialMessages
      ? sdkHistoryToTimeline(initialMessages)
      : createInitialState()
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const clientRef = useRef<ChatClient | null>(null);
  const wsManagerRef = useRef<WebSocketManager | null>(null);

  // WebSocket 回调 ref
  const wsCallbackRef = useRef(onWebSocketMessage);
  useEffect(() => {
    wsCallbackRef.current = onWebSocketMessage;
  }, [onWebSocketMessage]);

  // WebSocket 连接管理
  useEffect(() => {
    if (!enableWebSocket || !conversationId || !userId) {
      if (wsManagerRef.current) {
        wsManagerRef.current.destroy();
        wsManagerRef.current = null;
        setWsConnected(false);
      }
      return;
    }

    const wsUrl = wsBaseUrl || getWebSocketBaseUrl(baseUrl);
    const manager = createUserWebSocketManager(wsUrl, conversationId, userId);
    wsManagerRef.current = manager;

    const unsubState = manager.onStateChange((state) => {
      setWsConnected(state === "connected");
    });

    const unsubMessage = manager.onMessage((msg) => {
      wsCallbackRef.current?.(msg);
    });

    manager.connect();

    return () => {
      unsubState();
      unsubMessage();
      manager.destroy();
      wsManagerRef.current = null;
      setWsConnected(false);
    };
  }, [enableWebSocket, conversationId, userId, wsBaseUrl, baseUrl]);

  const sendMessage = useCallback(
    async (content: string, images?: ImageAttachment[]) => {
      if (!conversationId || !userId) {
        setError(new Error("Missing conversationId or userId"));
        return;
      }

      if (!content.trim() && (!images || images.length === 0)) {
        return;
      }

      setError(null);

      const userMessageId = crypto.randomUUID();
      const assistantTurnId = crypto.randomUUID();

      // 添加用户消息
      setStateInternal((prev) =>
        sdkAddUserMessage(prev, userMessageId, content.trim(), images)
      );

      // 开始助手 Turn
      setStateInternal((prev) => sdkStartAssistantTurn(prev, assistantTurnId));

      // 创建客户端
      const client = new ChatClient({ baseUrl });
      clientRef.current = client;

      try {
        for await (const event of client.stream({
          user_id: userId,
          conversation_id: conversationId,
          message: content.trim(),
          images,
        })) {
          setStateInternal((prev) => sdkTimelineReducer(prev, event));
          onEvent?.(event);
        }

        setStateInternal((prev) => sdkEndTurn(prev));
        onComplete?.();
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err);
          onError?.(err);
          setStateInternal((prev) => sdkClearTurn(prev, assistantTurnId));
        }
      } finally {
        clientRef.current = null;
      }
    },
    [baseUrl, conversationId, userId, onEvent, onError, onComplete]
  );

  const abort = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.abort();
      const currentTurnId = state.activeTurn.turnId;
      if (currentTurnId) {
        setStateInternal((prev) => sdkClearTurn(prev, currentTurnId));
      }
      clientRef.current = null;
    }
  }, [state.activeTurn.turnId]);

  const clearMessages = useCallback(() => {
    setStateInternal(createInitialState());
    setError(null);
  }, []);

  const initFromHistory = useCallback((messages: HistoryMessage[]) => {
    setStateInternal(sdkHistoryToTimeline(messages));
  }, []);

  const setState = useCallback((newState: TimelineState) => {
    setStateInternal(newState);
  }, []);

  const reload = useCallback(async () => {
    if (!loadHistory) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const messages = await loadHistory();
      setStateInternal(sdkHistoryToTimeline(messages));
    } catch (err) {
      if (err instanceof Error) {
        setError(err);
        onError?.(err);
      }
    } finally {
      setIsLoading(false);
    }
  }, [loadHistory, onError]);

  const wsSendMessage = useCallback(
    (action: string, payload: Record<string, unknown>) => {
      if (wsManagerRef.current) {
        wsManagerRef.current.send(action, payload);
      }
    },
    []
  );

  return {
    timeline: state.timeline,
    state,
    isStreaming: state.activeTurn.isStreaming,
    isLoading,
    error,
    sendMessage,
    abort,
    clearMessages,
    initFromHistory,
    reload,
    currentTurnId: state.activeTurn.turnId,
    setState,
    wsConnected,
    wsSendMessage,
  };
}
