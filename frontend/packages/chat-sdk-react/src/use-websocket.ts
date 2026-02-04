/**
 * useWebSocket Hook
 *
 * WebSocket 连接管理 Hook
 */

import { useCallback, useEffect, useRef, useState } from "react";
import {
  createUserWebSocketManager,
  createAgentWebSocketManager,
  type WebSocketManager,
  type ConnectionState,
  type WSMessage,
} from "@embedease/chat-sdk";

export interface UseWebSocketOptions {
  /** WebSocket 基础 URL */
  baseUrl?: string;

  /** 会话 ID */
  conversationId: string | null;

  /** 用户/客服 ID */
  userId: string | null;

  /** 是否启用 */
  enabled?: boolean;

  /** 角色类型 */
  role?: "user" | "agent";

  /** 消息处理器 */
  onMessage?: (message: WSMessage) => void;

  /** 状态变更处理器 */
  onStateChange?: (state: ConnectionState, prevState: ConnectionState) => void;

  /** 错误处理器 */
  onError?: (error: Error) => void;
}

export interface UseWebSocketReturn {
  /** 连接状态 */
  connectionState: ConnectionState;

  /** 是否已连接 */
  isConnected: boolean;

  /** 连接 ID */
  connectionId: string | null;

  /** 发送消息 */
  sendMessage: (action: string, payload: Record<string, unknown>) => string;

  /** 手动重连 */
  reconnect: () => void;

  /** 断开连接 */
  disconnect: () => void;
}

function getWebSocketBaseUrl(): string {
  if (typeof window === "undefined") return "";

  const envUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (envUrl) return envUrl;

  if (process.env.NODE_ENV === "development") {
    return "ws://127.0.0.1:8000";
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const {
    baseUrl,
    conversationId,
    userId,
    enabled = true,
    role = "user",
    onMessage,
    onStateChange,
    onError,
  } = options;

  const managerRef = useRef<WebSocketManager | null>(null);
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("disconnected");
  const [connectionId, setConnectionId] = useState<string | null>(null);

  // 使用 ref 存储回调
  const callbacksRef = useRef({ onMessage, onStateChange, onError });
  useEffect(() => {
    callbacksRef.current = { onMessage, onStateChange, onError };
  }, [onMessage, onStateChange, onError]);

  // 消息处理
  const handleMessage = useCallback((msg: WSMessage) => {
    if (msg.action === "system.connected") {
      const payload = msg.payload as { connection_id?: string };
      setConnectionId(payload.connection_id ?? null);
    }
    callbacksRef.current.onMessage?.(msg);
  }, []);

  // 状态变更处理
  const handleStateChange = useCallback(
    (state: ConnectionState, prevState: ConnectionState) => {
      setConnectionState(state);
      callbacksRef.current.onStateChange?.(state, prevState);
    },
    []
  );

  // 错误处理
  const handleError = useCallback((error: Error) => {
    callbacksRef.current.onError?.(error);
  }, []);

  // 创建和管理 WebSocket 连接
  useEffect(() => {
    if (!enabled || !conversationId || !userId) {
      if (managerRef.current) {
        managerRef.current.destroy();
        managerRef.current = null;
        setConnectionState("disconnected");
        setConnectionId(null);
      }
      return;
    }

    const wsUrl = baseUrl || getWebSocketBaseUrl();
    const manager =
      role === "agent"
        ? createAgentWebSocketManager(wsUrl, conversationId, userId)
        : createUserWebSocketManager(wsUrl, conversationId, userId);

    managerRef.current = manager;

    const unsubMessage = manager.onMessage(handleMessage);
    const unsubState = manager.onStateChange(handleStateChange);
    const unsubError = manager.onError(handleError);

    manager.connect();

    return () => {
      unsubMessage();
      unsubState();
      unsubError();
      manager.destroy();
      managerRef.current = null;
    };
  }, [
    enabled,
    conversationId,
    userId,
    baseUrl,
    role,
    handleMessage,
    handleStateChange,
    handleError,
  ]);

  const sendMessage = useCallback(
    (action: string, payload: Record<string, unknown>): string => {
      if (managerRef.current) {
        return managerRef.current.send(action, payload);
      }
      return "";
    },
    []
  );

  const reconnect = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.disconnect();
      managerRef.current.connect();
    }
  }, []);

  const disconnect = useCallback(() => {
    if (managerRef.current) {
      managerRef.current.disconnect();
    }
  }, []);

  return {
    connectionState,
    isConnected: connectionState === "connected",
    connectionId,
    sendMessage,
    reconnect,
    disconnect,
  };
}
