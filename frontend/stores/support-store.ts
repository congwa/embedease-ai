/**
 * 客服端状态管理 Store
 * 
 * 管理客服端的消息、连接状态、用户在线状态等
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type {
  ConversationState,
  RecentTaskStateSummary,
  ReviewStateSummary,
  SecondaryIssueStateSummary,
  SupportMessage,
  TicketStateSummary,
} from "@/types/websocket";

export interface SupportState {
  // 当前会话
  conversationId: string | null;
  
  // 连接状态
  isConnected: boolean;
  connectionId: string | null;
  
  // 会话状态
  conversationMode: "ai" | "pending" | "human" | "closed";
  handoffState: "ai" | "pending" | "human";
  operator: string | null;
  handoffReason: string | null;
  currentTicket: TicketStateSummary | null;
  reviewSummary: ReviewStateSummary | null;
  recentTasks: RecentTaskStateSummary[];
  secondaryIssues: SecondaryIssueStateSummary[];
  handoffSummary: Record<string, unknown> | null;
  
  // 用户在线状态
  userOnline: boolean;
  userLastOnlineAt: string | null;
  userTyping: boolean;
  
  // 消息列表
  messages: SupportMessage[];
  
  // 未读消息
  unreadCount: number;
  
  // Actions - 连接状态
  setConversationId: (id: string | null) => void;
  setConnected: (connected: boolean, connectionId?: string | null) => void;
  
  // Actions - 会话状态
  setHandoffState: (state: "ai" | "pending" | "human", operator?: string | null) => void;
  updateConversationState: (state: ConversationState) => void;
  
  // Actions - 用户状态
  setUserOnline: (online: boolean, lastOnlineAt?: string | null) => void;
  setUserTyping: (typing: boolean) => void;
  
  // Actions - 消息
  addMessage: (message: SupportMessage) => void;
  setMessages: (messages: SupportMessage[]) => void;
  updateMessage: (messageId: string, updates: Partial<SupportMessage>) => void;
  withdrawMessage: (messageId: string, withdrawnAt: string, withdrawnBy: string) => void;
  editMessage: (messageId: string, newContent: string, editedAt: string, editedBy: string) => void;
  deleteMessages: (messageIds: string[]) => void;
  
  // Actions - 未读
  setUnreadCount: (count: number) => void;
  
  // Actions - 重置
  reset: () => void;
}

const initialState = {
  conversationId: null,
  isConnected: false,
  connectionId: null,
  conversationMode: "ai" as const,
  handoffState: "ai" as const,
  operator: null,
  handoffReason: null,
  currentTicket: null,
  reviewSummary: null,
  recentTasks: [] as RecentTaskStateSummary[],
  secondaryIssues: [] as SecondaryIssueStateSummary[],
  handoffSummary: null,
  userOnline: false,
  userLastOnlineAt: null,
  userTyping: false,
  messages: [] as SupportMessage[],
  unreadCount: 0,
};

export const useSupportStore = create<SupportState>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    setConversationId: (id) => {
      const currentId = get().conversationId;
      if (currentId !== id) {
        // 切换会话时清空消息（但保留 handoffState，等待后端数据）
        set({
          conversationId: id,
          messages: [],
          isConnected: false,
          connectionId: null,
          // 注意：不重置 handoffState，等待 API 或 WebSocket 设置
          currentTicket: null,
          reviewSummary: null,
          recentTasks: [],
          secondaryIssues: [],
          handoffSummary: null,
          userOnline: false,
          userLastOnlineAt: null,
          userTyping: false,
          unreadCount: 0,
        });
      }
    },

    setConnected: (connected, connectionId = null) => {
      set({ isConnected: connected, connectionId });
    },

    setHandoffState: (state, operator = null) => {
      set({ handoffState: state, conversationMode: state, operator });
    },

    updateConversationState: (state) => {
      set({
        conversationMode: state.conversation_mode ?? "ai",
        handoffState: state.handoff_state,
        operator: state.operator ?? null,
        handoffReason: state.handoff_reason ?? null,
        currentTicket: state.current_ticket ?? null,
        reviewSummary: state.review_summary ?? null,
        recentTasks: state.recent_tasks ?? [],
        secondaryIssues: state.secondary_issues ?? [],
        handoffSummary: state.handoff_summary ?? null,
        userOnline: state.user_online ?? false,
        userLastOnlineAt: state.peer_last_online_at ?? null,
        unreadCount: state.unread_count ?? 0,
      });
    },

    setUserOnline: (online, lastOnlineAt = null) => {
      set({ userOnline: online, userLastOnlineAt: lastOnlineAt });
    },

    setUserTyping: (typing) => {
      set({ userTyping: typing });
    },

    /**
     * 向客服消息流追加或合并一条消息。
     *
     * 这个方法服务于客服端乐观发送和服务端真实回包的对齐场景：如果同一 message_id
     * 再次到达，则把送达/已读等真实状态合并进原消息，而不是重复插入。
     */
    addMessage: (message) => {
      set((state) => {
        const existingIndex = state.messages.findIndex((m) => m.id === message.id);
        if (existingIndex >= 0) {
          const updatedMessages = [...state.messages];
          updatedMessages[existingIndex] = {
            ...updatedMessages[existingIndex],
            ...message,
          };
          return { messages: updatedMessages };
        }
        return { messages: [...state.messages, message] };
      });
    },

    setMessages: (messages) => {
      set({ messages });
    },

    updateMessage: (messageId, updates) => {
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === messageId ? { ...m, ...updates } : m
        ),
      }));
    },

    withdrawMessage: (messageId, withdrawnAt, withdrawnBy) => {
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === messageId
            ? { ...m, is_withdrawn: true, withdrawn_at: withdrawnAt, withdrawn_by: withdrawnBy }
            : m
        ),
      }));
    },

    editMessage: (messageId, newContent, editedAt, editedBy) => {
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === messageId
            ? { ...m, content: newContent, is_edited: true, edited_at: editedAt, edited_by: editedBy }
            : m
        ),
      }));
    },

    deleteMessages: (messageIds) => {
      const idsSet = new Set(messageIds);
      set((state) => ({
        messages: state.messages.filter((m) => !idsSet.has(m.id)),
      }));
    },

    setUnreadCount: (count) => {
      set({ unreadCount: count });
    },

    reset: () => {
      set(initialState);
    },
  }))
);
