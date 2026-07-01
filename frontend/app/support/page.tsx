"use client";

/**
 * 客服工作台列表页
 *
 * 这个页面的业务职责，是给人工客服提供按用户聚合的会话队列视图，并支持实时看到
 * 待接入、高风险、返工和最新消息变化，帮助人工决定先处理谁。
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Headphones,
  RefreshCw,
  Flame,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  getSupportConversations,
  getSupportStats,
} from "@/lib/api/support";
import { buildSupportWorkbenchMonitoredConversations } from "@/lib/config/support-workbench-monitoring";
import { useSupportWorkbenchStore } from "@/stores";
import { useSupportWorkbenchRealtime } from "@/hooks/use-support-workbench-realtime";
import { UserList } from "./components/user-list";
import { ConversationPanel } from "./components/conversation-panel";
import { SupportQueueOverview } from "./components/support-queue-overview";

export default function SupportListPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // 使用 Store 管理状态
  const {
    conversations,
    userGroups,
    stats,
    selectedUserId,
    filter,
    sortBy,
    isLoading,
    error,
    setConversations,
    setStats,
    setSelectedUserId,
    setFilter,
    setSortBy,
    setLoading,
    setError,
    patchConversation,
  } = useSupportWorkbenchStore();

  // 初始化状态：防止首次渲染闪烁
  const [isInitialized, setIsInitialized] = useState(false);
  const isFirstLoad = useRef(true);
  const [agentId] = useState(() => {
    if (typeof window !== "undefined") {
      let id = localStorage.getItem("support_agent_id");
      if (!id) {
        id = Math.random().toString(36).slice(2, 10);
        localStorage.setItem("support_agent_id", id);
      }
      if (id.startsWith("agent_")) {
        id = id.slice(6);
        localStorage.setItem("support_agent_id", id);
      }
      return id;
    }
    return null;
  });
  const deepLinkConversationId =
    searchParams.get("conv_id") ?? searchParams.get("conversation_id");

  /**
   * 拉取全局客服统计。
   *
   * 这个方法服务于顶部全局红点和队列压力概览。统计必须独立于当前过滤条件，
   * 否则客服切换筛选后会误以为全局待接入数量发生变化。
   */
  const loadStats = useCallback(async () => {
    try {
      const statsData = await getSupportStats();
      setStats(statsData);
    } catch {
      // 统计刷新失败不打断当前列表使用，交给定时轮询和下一次事件刷新兜底
    }
  }, [setStats]);

  /**
   * 拉取当前过滤条件下的会话列表。
   *
   * 这个方法服务于客服工作台主队列，列表内容会随筛选条件变化，而顶部全局统计不在这里更新。
   */
  const loadConversations = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      const convData = await getSupportConversations(filter || undefined, sortBy);
      setConversations(
        convData.items.map((conversation) => ({
          ...conversation,
          lastMessage: conversation.last_message?.slice(0, 100) ?? undefined,
          lastMessageAt: conversation.last_message_at ?? undefined,
          lastMessageRole:
            conversation.last_message_role === "human_agent"
              ? "human"
              : conversation.last_message_role === "user" ||
                  conversation.last_message_role === "assistant"
                ? conversation.last_message_role
                : undefined,
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [filter, sortBy, setConversations, setLoading, setError]);

  /**
   * 同步刷新工作台主数据。
   *
   * 这个方法服务于首次进入和人工手动刷新场景，确保列表数据和顶部统计一起校准。
   */
  const loadWorkbench = useCallback(async (silent = false) => {
    await Promise.all([loadConversations(silent), loadStats()]);
  }, [loadConversations, loadStats]);

  // 使用 useLayoutEffect 在 DOM 绘制前同步初始化
  useLayoutEffect(() => {
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
      if (deepLinkConversationId) {
        router.replace(`/support/${deepLinkConversationId}`);
        return;
      }
      loadWorkbench().finally(() => {
        setIsInitialized(true);
      });
    }
  }, [deepLinkConversationId, loadWorkbench, router]);

  // 筛选/排序变化时重新加载
  useEffect(() => {
    if (isInitialized) {
      loadConversations();
    }
  }, [filter, sortBy, isInitialized, loadConversations]);

  // 定时静默刷新（不显示 loading）
  useEffect(() => {
    if (!isInitialized) return;
    const interval = setInterval(() => {
      void loadWorkbench(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [isInitialized, loadWorkbench]);

  // 当前选中的用户组
  const selectedGroup = selectedUserId
    ? userGroups.find((g) => g.userId === selectedUserId) || null
    : null;

  /**
   * 按实时事件粒度刷新列表或统计。
   *
   * 这个方法服务于列表页实时闭环：能本地补丁更新的先补丁，只有影响过滤结果或全局统计时
   * 才补拉接口，避免每条事件都整页重载。
   */
  const handleRealtimeSignal = useCallback((_: string, action: string) => {
    const shouldReloadConversations =
      action === "server.support_queue_changed" ||
      (
        filter !== null &&
        (
        action === "server.conversation_state" ||
        action === "server.handoff_started" ||
        action === "server.handoff_ended"
        )
      );
    const shouldRefreshStats =
      action === "server.message" ||
      action === "server.conversation_state" ||
      action === "server.support_queue_changed" ||
      action === "server.handoff_started" ||
      action === "server.handoff_ended";

    if (shouldReloadConversations && shouldRefreshStats) {
      void Promise.all([loadConversations(true), loadStats()]);
      return;
    }
    if (shouldReloadConversations) {
      void loadConversations(true);
      return;
    }
    if (shouldRefreshStats) {
      void loadStats();
    }
  }, [filter, loadConversations, loadStats]);

  const monitoredConversations = buildSupportWorkbenchMonitoredConversations(
    conversations,
    selectedGroup?.conversations ?? []
  );

  useSupportWorkbenchRealtime({
    conversations: monitoredConversations,
    agentId,
    enabled: isInitialized,
    onPatchConversation: patchConversation,
    onSignal: handleRealtimeSignal,
  });

  // 初始化前显示全屏 loading，避免闪烁
  if (!isInitialized) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-green-500 border-t-transparent" />
          <span className="text-sm text-zinc-500">加载中...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-zinc-50 dark:bg-zinc-900">
      {/* 顶部栏 */}
      <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center rounded-full bg-green-500">
            <Headphones className="h-4 w-4 text-white" />
            {stats && stats.pending_count > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
                {stats.pending_count > 99 ? "99+" : stats.pending_count}
              </span>
            )}
          </div>
          <div>
            <h1 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              客服工作台
            </h1>
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <span>{userGroups.length} 个用户</span>
              <span>•</span>
              <span>{conversations.length} 个会话</span>
              {stats && stats.total_unread > 0 && (
                <Badge variant="secondary" className="h-4 px-1 text-[10px] bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">
                  {stats.total_unread} 未读
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* 排序切换 */}
          <div className="flex rounded-md border border-zinc-200 dark:border-zinc-700 p-0.5">
            <button
              onClick={() => setSortBy("heat")}
              className={cn(
                "flex items-center gap-1 px-2.5 py-1 text-xs rounded transition-colors",
                sortBy === "heat"
                  ? "bg-orange-500 text-white"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              <Flame className="h-3 w-3" />
              热度
            </button>
            <button
              onClick={() => setSortBy("time")}
              className={cn(
                "flex items-center gap-1 px-2.5 py-1 text-xs rounded transition-colors",
                sortBy === "time"
                  ? "bg-blue-500 text-white"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              <Clock className="h-3 w-3" />
              时间
            </button>
          </div>

          {/* 状态筛选 */}
          <div className="flex rounded-md border border-zinc-200 dark:border-zinc-700 p-0.5">
            <button
              onClick={() => setFilter(null)}
              className={cn(
                "px-2.5 py-1 text-xs rounded transition-colors",
                filter === null
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              全部
            </button>
            <button
              onClick={() => setFilter("pending")}
              className={cn(
                "relative px-2.5 py-1 text-xs rounded transition-colors",
                filter === "pending"
                  ? "bg-yellow-500 text-white"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              等待
              {stats && stats.pending_count > 0 && filter !== "pending" && (
                <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-red-500" />
              )}
            </button>
            <button
              onClick={() => setFilter("human")}
              className={cn(
                "px-2.5 py-1 text-xs rounded transition-colors",
                filter === "human"
                  ? "bg-green-500 text-white"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              人工
            </button>
            <button
              onClick={() => setFilter("ai")}
              className={cn(
                "px-2.5 py-1 text-xs rounded transition-colors",
                filter === "ai"
                  ? "bg-zinc-500 text-white"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
              )}
            >
              AI
            </button>
          </div>

          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => loadWorkbench()}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          </Button>
        </div>
      </header>

      {/* 错误提示 */}
      {error && (
        <div className="mx-4 mt-2 p-2 text-sm text-red-600 bg-red-50 rounded-lg dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col">
        <SupportQueueOverview
          stats={stats}
          conversations={conversations}
          userGroups={userGroups}
          filter={filter}
        />

        {/* 主内容区：左右分栏 */}
        <main className="flex min-h-0 flex-1 overflow-hidden">
          {/* 左侧：用户列表 */}
          <aside className="w-80 flex-shrink-0 overflow-auto border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
            {isLoading && conversations.length === 0 ? (
              <div className="flex items-center justify-center py-20">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-green-500 border-t-transparent" />
              </div>
            ) : (
              <UserList
                groups={userGroups}
                selectedUserId={selectedUserId}
                onSelectUser={setSelectedUserId}
              />
            )}
          </aside>

          {/* 右侧：会话详情面板 */}
          <section className="flex-1 overflow-hidden bg-zinc-50 dark:bg-zinc-950">
            <ConversationPanel group={selectedGroup} />
          </section>
        </main>
      </div>
    </div>
  );
}
