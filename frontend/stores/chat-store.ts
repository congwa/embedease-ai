/**
 * 聊天状态管理 Store
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { ChatEvent, ImageAttachment } from "@/types/chat";
import { getConversationMessages } from "@/lib/api/conversations";
import { getApiBaseUrl } from "@/lib/api/client";
import {
  createChatStreamClient,
  createTimelineManager,
  type IChatStreamClient,
  type ITimelineManager,
} from "@/lib/chat-adapter";
import {
  type TimelineState,
  type TimelineItem,
  createInitialState,
  historyToTimeline,
} from "@/lib/timeline-utils";
import { useUserStore } from "./user-store";
import { useConversationStore } from "./conversation-store";

// 创建全局 Timeline 管理器实例
const globalTimelineManager = createTimelineManager();

interface ChatState {
  timelineState: TimelineState;
  isLoading: boolean;
  isLoadingMore: boolean;
  error: string | null;
  isHumanMode: boolean;
  _streamClient: IChatStreamClient | null;
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
  // WebSocket 消息处理
  addSupportEvent: (message: string, operator?: string) => void;
  addHumanAgentMessage: (content: string, operator?: string) => void;
  // 人工模式：添加用户消息到 timeline（不触发 AI 响应）
  addUserMessageOnly: (content: string) => void;
}

export const useChatStore = create<ChatState>()(
  subscribeWithSelector((set, get) => ({
    timelineState: globalTimelineManager.getState(),
    isLoading: false,
    isLoadingMore: false,
    error: null,
    isHumanMode: false,
    _streamClient: null,
    isStreaming: false,
    nextCursor: null,
    hasMore: false,
    currentAgentId: null,
    currentAgentName: null,

    timeline: () => get().timelineState.timeline,
    currentTurnId: () => get().timelineState.activeTurn.turnId,

    loadMessages: async (conversationId: string) => {
      if (!conversationId) {
        globalTimelineManager.reset();
        set({ timelineState: globalTimelineManager.getState(), nextCursor: null, hasMore: false });
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
        
        // 使用 Timeline 管理器从历史初始化
        globalTimelineManager.initFromHistory(messages);

        set({
          timelineState: globalTimelineManager.getState(),
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
        // 注意：loadMoreMessages 使用直接操作 state，因为 Timeline 管理器目前不支持 prepend
        const currentTimeline = globalTimelineManager.getState().timeline;
        const olderTimeline = historyToTimeline(olderMessages).timeline;
        
        // 更新 Timeline 管理器状态
        const newState = {
          ...globalTimelineManager.getState(),
          timeline: [...olderTimeline, ...currentTimeline],
        };
        globalTimelineManager.setState(newState);
        
        set({
          timelineState: globalTimelineManager.getState(),
          nextCursor: response.next_cursor,
          hasMore: response.has_more,
          isLoadingMore: false,
        });
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

      const isNewConversation = !conversationId;
      if (!conversationId) {
        // 设置跳过标志，防止 subscription 自动加载消息覆盖我们的 timeline
        setSkipNextLoad(true);
        const conversation = await useConversationStore.getState().createNewConversation();
        if (!conversation) {
          setSkipNextLoad(false);
          return;
        }
        conversationId = conversation.id;
      }

      set({ error: null });

      const userMessageId = crypto.randomUUID();
      
      // 如果是新会话，重置 Timeline 管理器
      if (isNewConversation) {
        globalTimelineManager.reset();
      }
      
      // 使用 Timeline 管理器添加用户消息
      globalTimelineManager.addUserMessage(userMessageId, content.trim(), images);
      set({ timelineState: globalTimelineManager.getState() });

      const assistantTurnId = crypto.randomUUID();
      globalTimelineManager.startAssistantTurn(assistantTurnId);
      set({ timelineState: globalTimelineManager.getState(), isStreaming: true });

      // 使用 Adapter 创建 SSE 客户端
      const client = createChatStreamClient(getApiBaseUrl());
      set({ _streamClient: client });

      try {
        for await (const event of client.stream({
          user_id: userId,
          conversation_id: conversationId,
          message: content.trim(),
          images,
        })) {
          get()._handleEvent(event);
        }

        globalTimelineManager.endTurn();
        set({ timelineState: globalTimelineManager.getState(), isStreaming: false });

        if (get().timelineState.timeline.length <= 2) {
          const title = content.slice(0, 50) + (content.length > 50 ? "..." : "");
          useConversationStore.getState().updateConversationTitle(conversationId, title);
        }
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          set({ error: err.message });
          globalTimelineManager.clearTurn(assistantTurnId);
          set({ timelineState: globalTimelineManager.getState() });
        }
      } finally {
        set({ _streamClient: null, isStreaming: false });
      }
    },

    clearMessages: () => {
      globalTimelineManager.reset();
      set({
        timelineState: globalTimelineManager.getState(),
        error: null,
      });
    },

    abortStream: () => {
      const client = get()._streamClient;
      if (client) {
        client.abort();
        const currentTurnId = get().timelineState.activeTurn.turnId;
        if (currentTurnId) {
          globalTimelineManager.clearTurn(currentTurnId);
          set({ timelineState: globalTimelineManager.getState() });
        }
        set({ _streamClient: null, isStreaming: false });
      }
    },

    setHumanMode: (isHuman: boolean) => {
      set({ isHumanMode: isHuman });
    },

    _handleEvent: (event: ChatEvent) => {
      // 使用 Timeline 管理器处理事件
      globalTimelineManager.dispatch(event);
      
      set((state) => {
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
          timelineState: globalTimelineManager.getState(),
          isHumanMode: newHumanMode,
          currentAgentId: newAgentId,
          currentAgentName: newAgentName,
        };
      });
    },

    _reset: () => {
      const client = get()._streamClient;
      if (client) {
        client.abort();
      }
      globalTimelineManager.reset();
      set({
        timelineState: globalTimelineManager.getState(),
        isLoading: false,
        isLoadingMore: false,
        error: null,
        isHumanMode: false,
        _streamClient: null,
        isStreaming: false,
        nextCursor: null,
        hasMore: false,
        currentAgentId: null,
        currentAgentName: null,
      });
    },

    // WebSocket 消息处理
    addSupportEvent: (message: string, operator?: string) => {
      const now = Date.now();
      const event: ChatEvent = {
        v: 1,
        id: crypto.randomUUID(),
        seq: now,
        ts: now,
        conversation_id: useConversationStore.getState().currentConversationId || "",
        type: "support.handoff_started",
        payload: { message, operator },
      };
      get()._handleEvent(event);
    },

    addHumanAgentMessage: (content: string, operator?: string) => {
      const now = Date.now();
      const event: ChatEvent = {
        v: 1,
        id: crypto.randomUUID(),
        seq: now,
        ts: now,
        conversation_id: useConversationStore.getState().currentConversationId || "",
        type: "support.human_message",
        payload: { content, operator, message_id: crypto.randomUUID() },
      };
      get()._handleEvent(event);
    },

    // 人工模式：只添加用户消息到 timeline，不触发 AI 响应
    addUserMessageOnly: (content: string) => {
      const userMessageId = crypto.randomUUID();
      globalTimelineManager.addUserMessage(userMessageId, content.trim());
      set({ timelineState: globalTimelineManager.getState() });
    },
  }))
);

// 订阅 ConversationStore，会话切换时加载消息
let prevConversationId: string | null = null;
let skipNextLoad = false; // 标志位：跳过下次加载（新会话创建时）

export function setSkipNextLoad(skip: boolean) {
  skipNextLoad = skip;
}

useConversationStore.subscribe((state) => {
  const conversationId = state.currentConversationId;
  if (conversationId !== prevConversationId) {
    prevConversationId = conversationId;
    if (conversationId) {
      // 如果设置了跳过标志，不加载消息（新会话创建时由 sendMessage 处理）
      if (skipNextLoad) {
        skipNextLoad = false;
        return;
      }
      useChatStore.getState().loadMessages(conversationId);
    } else {
      useChatStore.getState().clearMessages();
    }
  }
});
