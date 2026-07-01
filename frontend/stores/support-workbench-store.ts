/**
 * 客服工作台状态管理 Store
 *
 * 这个文件的业务职责，是把客服列表页所需的会话、用户分组、统计和队列优先级
 * 统一收敛到一个 store 中，避免列表页和分组面板各自重复计算。
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { SupportConversation, SupportStats } from "@/lib/api/support";

// 带最新消息的会话
export interface ConversationWithPreview extends SupportConversation {
  lastMessage?: string;
  lastMessageAt?: string;
  lastMessageRole?: "user" | "assistant" | "human";
}

// 按用户聚合的会话组
export interface UserConversationGroup {
  userId: string;
  conversations: ConversationWithPreview[];
  totalUnread: number;
  maxHeatScore: number;
  latestUpdate: string;
  priorityState: "pending" | "human" | "ai";
  hasOnlineUser: boolean;
  pendingConversationCount: number;
  highRiskConversationCount: number;
  reworkConversationCount: number;
  activeComplaintCount: number;
  // 最新消息预览
  lastMessage?: string;
  lastMessageAt?: string;
}

export interface SupportWorkbenchState {
  // 会话列表
  conversations: ConversationWithPreview[];
  
  // 用户分组
  userGroups: UserConversationGroup[];
  
  // 统计数据
  stats: SupportStats | null;
  
  // 选中的用户
  selectedUserId: string | null;
  
  // 筛选和排序
  filter: string | null;
  sortBy: "heat" | "time";
  
  // 加载状态
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setConversations: (conversations: ConversationWithPreview[]) => void;
  setStats: (stats: SupportStats) => void;
  setSelectedUserId: (userId: string | null) => void;
  setFilter: (filter: string | null) => void;
  setSortBy: (sortBy: "heat" | "time") => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  
  // 更新单个会话的最新消息
  updateConversationPreview: (
    conversationId: string,
    lastMessage: string,
    lastMessageAt: string,
    lastMessageRole: "user" | "assistant" | "human"
  ) => void;
  patchConversation: (
    conversationId: string,
    updates: Partial<ConversationWithPreview>
  ) => void;
  
  // 重置
  reset: () => void;
}

/**
 * 按用户聚合会话并生成队列优先级信号。
 *
 * 这个方法服务于客服列表页，让人工在用户维度先看出谁有待接入、高风险或返工中的问题单。
 */
function groupConversationsByUser(
  conversations: ConversationWithPreview[],
  sortBy: "heat" | "time"
): UserConversationGroup[] {
  const groupMap = new Map<string, ConversationWithPreview[]>();

  conversations.forEach((conv) => {
    const existing = groupMap.get(conv.user_id) || [];
    existing.push(conv);
    groupMap.set(conv.user_id, existing);
  });

  const groups: UserConversationGroup[] = [];

  groupMap.forEach((convs, userId) => {
    // 按更新时间降序
    convs.sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );

    const totalUnread = convs.reduce((sum, c) => sum + c.unread_count, 0);
    const maxHeatScore = Math.max(...convs.map((c) => c.heat_score));
    const latestUpdate = convs[0].updated_at;
    const hasOnlineUser = convs.some((c) => c.user_online);
    const pendingConversationCount = convs.filter((c) => c.handoff_state === "pending").length;
    const highRiskConversationCount = convs.filter((c) => c.risk_level === "high").length;
    const reworkConversationCount = convs.filter(
      (c) => c.review_status === "rejected" || c.ticket_status === "rework_required" || c.ticket_status === "blocked"
    ).length;
    const activeComplaintCount = convs.filter(
      (c) => c.ticket_status && c.ticket_status !== "resolved" && c.ticket_status !== "closed"
    ).length;

    // 找最新的消息
    const convWithLastMsg = convs.find((c) => c.lastMessage);
    const lastMessage = convWithLastMsg?.lastMessage;
    const lastMessageAt = convWithLastMsg?.lastMessageAt;

    let priorityState: "pending" | "human" | "ai" = "ai";
    if (convs.some((c) => c.handoff_state === "pending")) {
      priorityState = "pending";
    } else if (convs.some((c) => c.handoff_state === "human")) {
      priorityState = "human";
    }

    groups.push({
      userId,
      conversations: convs,
      totalUnread,
      maxHeatScore,
      latestUpdate,
      priorityState,
      hasOnlineUser,
      pendingConversationCount,
      highRiskConversationCount,
      reworkConversationCount,
      activeComplaintCount,
      lastMessage,
      lastMessageAt,
    });
  });

  // 排序
  return groups.sort((a, b) => {
    const priorityOrder = { pending: 0, human: 1, ai: 2 };
    const priorityDiff = priorityOrder[a.priorityState] - priorityOrder[b.priorityState];
    if (priorityDiff !== 0) return priorityDiff;

    if (sortBy === "heat") {
      return b.maxHeatScore - a.maxHeatScore;
    }
    return new Date(b.latestUpdate).getTime() - new Date(a.latestUpdate).getTime();
  });
}

const initialState = {
  conversations: [] as ConversationWithPreview[],
  userGroups: [] as UserConversationGroup[],
  stats: null as SupportStats | null,
  selectedUserId: null as string | null,
  filter: null as string | null,
  sortBy: "heat" as const,
  isLoading: true,
  error: null as string | null,
};

export const useSupportWorkbenchStore = create<SupportWorkbenchState>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    setConversations: (conversations) => {
      const { sortBy, selectedUserId } = get();
      const userGroups = groupConversationsByUser(conversations, sortBy);
      
      // 自动选择第一个用户（如果当前没有选中）
      const newSelectedUserId =
        selectedUserId && userGroups.some((g) => g.userId === selectedUserId)
          ? selectedUserId
          : userGroups.length > 0
          ? userGroups[0].userId
          : null;

      set({
        conversations,
        userGroups,
        selectedUserId: newSelectedUserId,
      });
    },

    setStats: (stats) => {
      set({ stats });
    },

    setSelectedUserId: (userId) => {
      set({ selectedUserId: userId });
    },

    setFilter: (filter) => {
      set({ filter });
    },

    setSortBy: (sortBy) => {
      const { conversations } = get();
      const userGroups = groupConversationsByUser(conversations, sortBy);
      set({ sortBy, userGroups });
    },

    setLoading: (isLoading) => {
      set({ isLoading });
    },

    setError: (error) => {
      set({ error });
    },

    updateConversationPreview: (conversationId, lastMessage, lastMessageAt, lastMessageRole) => {
      const { conversations, sortBy } = get();
      const updated = conversations.map((c) =>
        c.id === conversationId
          ? { ...c, lastMessage, lastMessageAt, lastMessageRole }
          : c
      );
      const userGroups = groupConversationsByUser(updated, sortBy);
      set({ conversations: updated, userGroups });
    },

    /**
     * 按会话增量更新工作台卡片数据。
     *
     * 这个方法服务于列表页实时订阅，在不重新请求整页数据的情况下把单个会话的状态、
     * 风险、最新消息和工单快照更新到当前分组视图中。
     */
    patchConversation: (conversationId, updates) => {
      const { conversations, sortBy } = get();
      const updated = conversations.map((conversation) =>
        conversation.id === conversationId
          ? { ...conversation, ...updates }
          : conversation
      );
      const userGroups = groupConversationsByUser(updated, sortBy);
      set({ conversations: updated, userGroups });
    },

    reset: () => {
      set(initialState);
    },
  }))
);
