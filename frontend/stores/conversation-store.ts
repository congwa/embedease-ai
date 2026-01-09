/**
 * 会话列表状态管理 Store
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { Conversation } from "@/types/conversation";
import {
  getConversations as getUserConversations,
  createConversation,
  deleteConversation,
} from "@/lib/api/conversations";
import { useUserStore } from "./user-store";

interface ConversationState {
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  error: string | null;

  loadConversations: () => Promise<void>;
  createNewConversation: () => Promise<Conversation | null>;
  removeConversation: (id: string) => Promise<void>;
  selectConversation: (id: string) => void;
  updateConversationTitle: (id: string, title: string) => void;
  clearCurrentConversation: () => void;
  _reset: () => void;
}

export const useConversationStore = create<ConversationState>()(
  subscribeWithSelector((set, get) => ({
    conversations: [],
    currentConversationId: null,
    isLoading: false,
    error: null,

    loadConversations: async () => {
      const userId = useUserStore.getState().userId;
      if (!userId) return;

      set({ isLoading: true, error: null });
      try {
        const data = await getUserConversations(userId);
        set({ conversations: data, isLoading: false });
        console.log("[ConversationStore] 加载了", data.length, "个会话");
      } catch (error) {
        console.error("[ConversationStore] 加载失败:", error);
        set({ error: "加载会话失败", isLoading: false });
      }
    },

    createNewConversation: async () => {
      const userId = useUserStore.getState().userId;
      if (!userId) return null;

      try {
        const conversation = await createConversation({ user_id: userId });
        set((state) => ({
          conversations: [conversation, ...state.conversations],
          currentConversationId: conversation.id,
        }));
        console.log("[ConversationStore] 创建新会话:", conversation.id);
        return conversation;
      } catch (error) {
        console.error("[ConversationStore] 创建失败:", error);
        return null;
      }
    },

    removeConversation: async (id: string) => {
      try {
        await deleteConversation(id);
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
          currentConversationId:
            state.currentConversationId === id ? null : state.currentConversationId,
        }));
        console.log("[ConversationStore] 删除会话:", id);
      } catch (error) {
        console.error("[ConversationStore] 删除失败:", error);
      }
    },

    selectConversation: (id: string) => {
      set({ currentConversationId: id });
      console.log("[ConversationStore] 选择会话:", id);
    },

    updateConversationTitle: (id: string, title: string) => {
      set((state) => ({
        conversations: state.conversations.map((c) =>
          c.id === id ? { ...c, title } : c
        ),
      }));
    },

    clearCurrentConversation: () => {
      set({ currentConversationId: null });
    },

    _reset: () => {
      set({
        conversations: [],
        currentConversationId: null,
        isLoading: false,
        error: null,
      });
    },
  }))
);

// 订阅 UserStore，用户变化时重置并加载会话
let prevUserId: string | null = null;
useUserStore.subscribe((state) => {
  const userId = state.userId;
  if (userId !== prevUserId) {
    prevUserId = userId;
    useConversationStore.getState()._reset();
    if (userId) {
      useConversationStore.getState().loadConversations();
    }
  }
});
