/**
 * 客服工作台实时订阅 Hook
 *
 * 这个文件的业务职责，是为客服列表页当前选中的用户组建立轻量多会话 WebSocket 订阅，
 * 让会话卡片可以实时更新未读、风险、工单状态和服务模式，而不是完全依赖轮询。
 */

"use client";

import { useEffect, useRef } from "react";
import {
  createAgentWebSocketManager,
  createSupportQueueWebSocketManager,
  type WSMessage,
  type WebSocketManager,
} from "@/lib/websocket";
import type {
  ConnectedPayload,
  ConversationStatePayload,
  HandoffEndedPayload,
  HandoffStartedPayload,
  ReviewUpdatedPayload,
  ServerMessagePayload,
  SupportQueueChangedPayload,
  TicketUpdatedPayload,
  UserPresencePayload,
} from "@/types/websocket";
import type { ConversationWithPreview } from "@/stores/support-workbench-store";

interface UseSupportWorkbenchRealtimeOptions {
  conversations: ConversationWithPreview[];
  agentId: string | null;
  enabled?: boolean;
  onPatchConversation: (
    conversationId: string,
    updates: Partial<ConversationWithPreview>
  ) => void;
  onSignal?: (conversationId: string, action: string) => void;
}

/**
 * 把客服 WebSocket 消息转换成会话卡片增量更新。
 *
 * 这个方法服务于列表页实时刷新，把底层协议字段翻译成卡片真正关心的展示数据。
 */
function buildConversationPatchFromMessage(
  message: WSMessage,
  currentConversation: ConversationWithPreview
): Partial<ConversationWithPreview> | null {
  switch (message.action) {
    case "system.connected": {
      const payload = message.payload as unknown as ConnectedPayload;
      return {
        handoff_state: payload.handoff_state,
        user_online: payload.peer_online,
        unread_count: payload.unread_count,
        ticket_status: payload.current_ticket?.status ?? currentConversation.ticket_status,
        current_ticket_id: payload.current_ticket?.id ?? currentConversation.current_ticket_id,
        primary_issue_tag:
          payload.current_ticket?.primary_issue_tag ?? currentConversation.primary_issue_tag,
        current_agent_tag:
          payload.current_ticket?.current_agent_tag ?? currentConversation.current_agent_tag,
        risk_level: payload.current_ticket?.risk_level ?? currentConversation.risk_level,
        review_status: payload.review_summary?.status ?? currentConversation.review_status,
        review_score: payload.review_summary?.score ?? currentConversation.review_score,
      };
    }

    case "server.message": {
      const payload = message.payload as unknown as ServerMessagePayload;
      const nextUnreadCount =
        payload.role === "user"
          ? (currentConversation.unread_count ?? 0) + 1
          : currentConversation.unread_count;
      return {
        lastMessage: payload.content?.slice(0, 100) ?? currentConversation.lastMessage,
        lastMessageAt: payload.created_at ?? currentConversation.lastMessageAt,
        lastMessageRole:
          payload.role === "human_agent"
            ? "human"
            : (payload.role as "user" | "assistant" | "human"),
        unread_count: nextUnreadCount,
        updated_at: payload.created_at ?? currentConversation.updated_at,
      };
    }

    case "server.conversation_state": {
      const payload = message.payload as unknown as ConversationStatePayload;
      return {
        handoff_state: payload.handoff_state,
        handoff_operator: payload.operator ?? currentConversation.handoff_operator,
        handoff_reason: payload.handoff_reason ?? currentConversation.handoff_reason,
        user_online: payload.user_online ?? currentConversation.user_online,
        unread_count: payload.unread_count ?? currentConversation.unread_count,
        ticket_status: payload.current_ticket?.status ?? currentConversation.ticket_status,
        current_ticket_id: payload.current_ticket?.id ?? currentConversation.current_ticket_id,
        primary_issue_tag:
          payload.current_ticket?.primary_issue_tag ?? currentConversation.primary_issue_tag,
        current_agent_tag:
          payload.current_ticket?.current_agent_tag ?? currentConversation.current_agent_tag,
        risk_level: payload.current_ticket?.risk_level ?? currentConversation.risk_level,
        review_status: payload.review_summary?.status ?? currentConversation.review_status,
        review_score: payload.review_summary?.score ?? currentConversation.review_score,
        secondary_issue_detected:
          payload.current_ticket?.secondary_issue_detected ??
          currentConversation.secondary_issue_detected,
      };
    }

    case "server.ticket_updated": {
      const payload = message.payload as unknown as TicketUpdatedPayload;
      return {
        current_ticket_id: payload.ticket.id,
        ticket_status: payload.ticket.status,
        primary_issue_tag: payload.ticket.primary_issue_tag ?? currentConversation.primary_issue_tag,
        current_agent_tag: payload.ticket.current_agent_tag ?? currentConversation.current_agent_tag,
        risk_level: payload.ticket.risk_level ?? currentConversation.risk_level,
        secondary_issue_detected:
          payload.ticket.secondary_issue_detected ?? currentConversation.secondary_issue_detected,
        updated_at: payload.ticket.updated_at ?? new Date().toISOString(),
      };
    }

    case "server.review_updated": {
      const payload = message.payload as unknown as ReviewUpdatedPayload;
      return {
        review_status: payload.review_summary.status,
        review_score: payload.review_summary.score ?? currentConversation.review_score,
        risk_level: payload.review_summary.risk_level ?? currentConversation.risk_level,
        updated_at: payload.review_summary.created_at ?? new Date().toISOString(),
      };
    }

    case "server.user_online": {
      const payload = message.payload as unknown as UserPresencePayload;
      return {
        user_online: payload.online,
      };
    }

    case "server.user_offline": {
      const payload = message.payload as unknown as UserPresencePayload;
      return {
        user_online: payload.online,
      };
    }

    case "server.handoff_started": {
      const payload = message.payload as unknown as HandoffStartedPayload;
      return {
        handoff_state: "human",
        handoff_operator: payload.operator,
        handoff_reason: payload.reason ?? currentConversation.handoff_reason,
        updated_at: new Date().toISOString(),
      };
    }

    case "server.handoff_ended": {
      const payload = message.payload as unknown as HandoffEndedPayload;
      return {
        handoff_state: "ai",
        handoff_operator: payload.operator ?? null,
        handoff_reason: null,
        updated_at: new Date().toISOString(),
      };
    }

    default:
      return null;
  }
}

/**
 * 客服工作台实时订阅 Hook。
 *
 * 这个 Hook 只为当前选中用户组的会话建立订阅，避免列表页对全部会话同时建连接。
 */
export function useSupportWorkbenchRealtime({
  conversations,
  agentId,
  enabled = true,
  onPatchConversation,
  onSignal,
}: UseSupportWorkbenchRealtimeOptions) {
  const managersRef = useRef<Map<string, WebSocketManager>>(new Map());
  const globalQueueManagerRef = useRef<WebSocketManager | null>(null);
  const conversationsRef = useRef<Map<string, ConversationWithPreview>>(new Map());
  const onPatchConversationRef = useRef(onPatchConversation);
  const onSignalRef = useRef(onSignal);
  const agentIdRef = useRef<string | null>(agentId);
  const signalTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    onPatchConversationRef.current = onPatchConversation;
  }, [onPatchConversation]);

  useEffect(() => {
    onSignalRef.current = onSignal;
  }, [onSignal]);

  useEffect(() => {
    conversationsRef.current = new Map(conversations.map((conversation) => [conversation.id, conversation]));
  }, [conversations]);

  /**
   * 根据当前选中的会话集合建立或回收连接。
   *
   * 这个副作用服务于用户在列表页切换不同用户组时，只维护当前需要的那一组会话连接。
   */
  useEffect(() => {
    if (agentIdRef.current !== agentId) {
      managersRef.current.forEach((manager) => manager.destroy());
      managersRef.current.clear();
      globalQueueManagerRef.current?.destroy();
      globalQueueManagerRef.current = null;
      agentIdRef.current = agentId;
    }

    if (!enabled || !agentId) {
      managersRef.current.forEach((manager) => manager.destroy());
      managersRef.current.clear();
      globalQueueManagerRef.current?.destroy();
      globalQueueManagerRef.current = null;
      return;
    }

    if (!globalQueueManagerRef.current) {
      const globalQueueManager = createSupportQueueWebSocketManager("", agentId, {
        maxReconnectAttempts: 3,
        initialReconnectDelay: 1000,
        maxReconnectDelay: 5000,
      });
      globalQueueManager.onMessage((message) => {
        if (message.action !== "server.support_queue_changed") {
          return;
        }

        const payload = message.payload as unknown as SupportQueueChangedPayload;
        // 这个全局连接服务于“当前没有任何目标会话订阅，也要知道队列变了”的场景。
        if (signalTimerRef.current) {
          clearTimeout(signalTimerRef.current);
        }
        signalTimerRef.current = setTimeout(() => {
          onSignalRef.current?.(payload.conversation_id, message.action);
        }, 200);
      });
      globalQueueManager.connect();
      globalQueueManagerRef.current = globalQueueManager;
    }

    const targetConversationIds = new Set(conversations.map((conversation) => conversation.id));

    managersRef.current.forEach((manager, conversationId) => {
      if (!targetConversationIds.has(conversationId)) {
        manager.destroy();
        managersRef.current.delete(conversationId);
      }
    });

    conversations.forEach((conversation) => {
      if (managersRef.current.has(conversation.id)) {
        return;
      }

      const manager = createAgentWebSocketManager("", conversation.id, agentId, {
        maxReconnectAttempts: 3,
        initialReconnectDelay: 1000,
        maxReconnectDelay: 5000,
      });

      manager.onMessage((message) => {
        if (message.action === "server.support_queue_changed") {
          // 这类跨会话信号统一由独立的全局队列连接处理，避免多条会话连接重复消费。
          return;
        }

        const latestConversation = conversationsRef.current.get(conversation.id);
        if (!latestConversation) {
          return;
        }

        const patch = buildConversationPatchFromMessage(message, latestConversation);
        if (!patch) {
          return;
        }

        onPatchConversationRef.current(conversation.id, patch);

        if (
          message.action === "server.message" ||
          message.action === "server.conversation_state" ||
          message.action === "server.ticket_updated" ||
          message.action === "server.review_updated" ||
          message.action === "server.handoff_started" ||
          message.action === "server.handoff_ended"
        ) {
          if (signalTimerRef.current) {
            clearTimeout(signalTimerRef.current);
          }
          signalTimerRef.current = setTimeout(() => {
            onSignalRef.current?.(conversation.id, message.action);
          }, 500);
        }
      });

      manager.connect();
      managersRef.current.set(conversation.id, manager);
    });
  }, [agentId, conversations, enabled]);

  /**
   * 页面卸载时统一关闭所有连接。
   *
   * 这个副作用服务于防止客服离开列表页后仍然保留多会话订阅连接。
   */
  useEffect(() => {
    const managers = managersRef.current;
    const signalTimer = signalTimerRef.current;

    return () => {
      if (signalTimer) {
        clearTimeout(signalTimer);
      }
      globalQueueManagerRef.current?.destroy();
      globalQueueManagerRef.current = null;
      managers.forEach((manager) => manager.destroy());
      managers.clear();
    };
  }, []);
}
