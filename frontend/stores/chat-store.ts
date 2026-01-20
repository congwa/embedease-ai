/**
 * 聊天状态管理 Store
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { ChatEvent, ImageAttachment } from "@/types/chat";
import { getConversationMessages } from "@/lib/api/conversations";
import { streamChat, type StreamChatController } from "@/lib/api/chat";
import {
  type TimelineState,
  type TimelineItem,
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  timelineReducer,
  clearTurn,
  endTurn,
  historyToTimeline,
} from "@/lib/timeline-utils";
import { useUserStore } from "./user-store";
import { useConversationStore } from "./conversation-store";

interface ChatState {
  timelineState: TimelineState;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  isHumanMode: boolean;
  streamController: StreamChatController | null;
  isStreaming: boolean;
  // 分页状态
  nextCursor: string | null;
  hasMore: boolean;
  // Supervisor 状态
  currentAgentId: string | null;
  currentAgentName: string | null;

  timeline: () => TimelineItem[];
  currentTurnId: () => string | null;

  loadMessages: (conversationId: string) => Promise<void>;
  loadMoreMessages: (conversationId: string) => Promise<void>;
  sendMessage: (content: string, images?: ImageAttachment[]) => Promise<void>;
  clearMessages: () => void;
  abortStream: () => void;
  setHumanMode: (isHuman: boolean) => void;

  _handleEvent: (event: ChatEvent) => void;
  _reset: () => void;
}

export const useChatStore = create<ChatState>()(
  subscribeWithSelector((set, get) => ({
    timelineState: createInitialState(),
    isLoading: false,
    isLoadingMore: false,
    error: null,
    isHumanMode: false,
    streamController: null,
    isStreaming: false,
    nextCursor: null,
    hasMore: false,
    currentAgentId: null,
    currentAgentName: null,

    timeline: () => get().timelineState.timeline,
    currentTurnId: () => get().timelineState.activeTurn.turnId,

    loadMessages: async (conversationId: string) => {
      if (!conversationId) {
        set({ timelineState: createInitialState(), nextCursor: null, hasMore: false });
        return;
      }

      if (get().isStreaming) {
        console.log("[ChatStore] 正在流式传输，跳过加载");
        return;
      }

      set({ isLoading: true, error: null });
      try {
        const response = await getConversationMessages(conversationId, { limit: 50 });
        const messages = response.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant" | "system",
          content: msg.content,
          products: msg.products ? JSON.parse(msg.products) : undefined,
        }));
        const newState = historyToTimeline(messages);

        set({
          timelineState: newState,
          nextCursor: response.next_cursor,
          hasMore: response.has_more,
          isLoading: false,
        });
      } catch (err) {
        console.error("[ChatStore] 加载消息失败:", err);
        set({ error: "加载消息失败", isLoading: false });
      }
    },

    loadMoreMessages: async (conversationId: string) => {
      const { nextCursor, hasMore, isLoadingMore, isStreaming } = get();
      
      if (!conversationId || !hasMore || !nextCursor || isLoadingMore || isStreaming) {
        return;
      }

      set({ isLoadingMore: true });
      try {
        const response = await getConversationMessages(conversationId, {
          cursor: nextCursor,
          limit: 50,
        });
        
        const olderMessages = response.messages.map((msg) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant" | "system",
          content: msg.content,
          products: msg.products ? JSON.parse(msg.products) : undefined,
        }));
        
        // 将旧消息添加到现有 timeline 的前面
        const currentTimeline = get().timelineState.timeline;
        const olderTimeline = historyToTimeline(olderMessages).timeline;
        
        set((state) => ({
          timelineState: {
            ...state.timelineState,
            timeline: [...olderTimeline, ...currentTimeline],
          },
          nextCursor: response.next_cursor,
          hasMore: response.has_more,
          isLoadingMore: false,
        }));
      } catch (err) {
        console.error("[ChatStore] 加载更多消息失败:", err);
        set({ isLoadingMore: false });
      }
    },

    sendMessage: async (content: string, images?: ImageAttachment[]) => {
      const userId = useUserStore.getState().userId;
      let conversationId = useConversationStore.getState().currentConversationId;

      if (!userId || (!content.trim() && (!images || images.length === 0))) {
        return;
      }

      if (!conversationId) {
        const conversation = await useConversationStore.getState().createNewConversation();
        if (!conversation) return;
        conversationId = conversation.id;
      }

      set({ error: null });

      const userMessageId = crypto.randomUUID();
      set((state) => ({
        timelineState: addUserMessage(state.timelineState, userMessageId, content.trim(), images),
      }));

      const assistantTurnId = crypto.randomUUID();
      set((state) => ({
        timelineState: startAssistantTurn(state.timelineState, assistantTurnId),
        isStreaming: true,
      }));

      const controller: StreamChatController = { abort: () => {} };
      set({ streamController: controller });

      try {
        for await (const event of streamChat(
          {
            user_id: userId,
            conversation_id: conversationId,
            message: content.trim(),
            images,
          },
          controller
        )) {
          get()._handleEvent(event);
        }

        set((state) => ({
          timelineState: endTurn(state.timelineState),
          isStreaming: false,
        }));

        if (get().timelineState.timeline.length <= 2) {
          const title = content.slice(0, 50) + (content.length > 50 ? "..." : "");
          useConversationStore.getState().updateConversationTitle(conversationId, title);
        }
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          set({ error: err.message });
          set((state) => ({
            timelineState: clearTurn(state.timelineState, assistantTurnId),
          }));
        }
      } finally {
        set({ streamController: null, isStreaming: false });
      }
    },

    clearMessages: () => {
      set({
        timelineState: createInitialState(),
        error: null,
      });
    },

    abortStream: () => {
      const controller = get().streamController;
      if (controller) {
        controller.abort();
        const currentTurnId = get().timelineState.activeTurn.turnId;
        if (currentTurnId) {
          set((state) => ({
            timelineState: clearTurn(state.timelineState, currentTurnId),
          }));
        }
        set({ streamController: null, isStreaming: false });
      }
    },

    setHumanMode: (isHuman: boolean) => {
      set({ isHumanMode: isHuman });
    },

    _handleEvent: (event: ChatEvent) => {
      set((state) => {
        let newTimelineState = timelineReducer(state.timelineState, event);
        let newHumanMode = state.isHumanMode;
        let newAgentId = state.currentAgentId;
        let newAgentName = state.currentAgentName;

        if (event.type === "meta.start") {
          const payload = event.payload as { mode?: string };
          if (payload.mode === "human") {
            newHumanMode = true;
          }
        }

        // Supervisor 事件处理
        if (event.type === "agent.routed" || event.type === "agent.handoff") {
          const payload = event.payload as { target_agent?: string; target_agent_name?: string; to_agent?: string; to_agent_name?: string };
          newAgentId = payload.target_agent || payload.to_agent || null;
          newAgentName = payload.target_agent_name || payload.to_agent_name || null;
        }

        if (event.type === "agent.complete") {
          // Agent 完成后可以清除或保持，这里保持显示
        }

        return {
          timelineState: newTimelineState,
          isHumanMode: newHumanMode,
          currentAgentId: newAgentId,
          currentAgentName: newAgentName,
        };
      });
    },

    _reset: () => {
      const controller = get().streamController;
      if (controller) {
        controller.abort();
      }
      set({
        timelineState: createInitialState(),
        isLoading: false,
        isLoadingMore: false,
        error: null,
        isHumanMode: false,
        streamController: null,
        isStreaming: false,
        nextCursor: null,
        hasMore: false,
        currentAgentId: null,
        currentAgentName: null,
      });
    },
  }))
);

// 订阅 ConversationStore，会话切换时加载消息
let prevConversationId: string | null = null;
useConversationStore.subscribe((state) => {
  const conversationId = state.currentConversationId;
  if (conversationId !== prevConversationId) {
    prevConversationId = conversationId;
    if (conversationId) {
      useChatStore.getState().loadMessages(conversationId);
    } else {
      useChatStore.getState().clearMessages();
    }
  }
});
