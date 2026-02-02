"use client";

import { useCallback, useEffect } from "react";
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
  getConversationDetail,
} from "@/lib/api/support";
import { useSupportWorkbenchStore } from "@/stores";
import { UserList } from "./components/user-list";
import { ConversationPanel } from "./components/conversation-panel";

export default function SupportListPage() {
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
    updateConversationPreview,
  } = useSupportWorkbenchStore();

  // 加载会话列表
  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [convData, statsData] = await Promise.all([
        getSupportConversations(filter || undefined, sortBy),
        getSupportStats(),
      ]);
      setConversations(convData.items);
      setStats(statsData);

      // 异步加载每个会话的最新消息
      convData.items.forEach(async (conv) => {
        try {
          const detail = await getConversationDetail(conv.id);
          if (detail.messages && detail.messages.length > 0) {
            const lastMsg = detail.messages[detail.messages.length - 1];
            updateConversationPreview(
              conv.id,
              lastMsg.content.slice(0, 100),
              lastMsg.created_at,
              lastMsg.role as "user" | "assistant" | "human"
            );
          }
        } catch {
          // 忽略单个会话加载失败
        }
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [filter, sortBy, setConversations, setStats, setLoading, setError, updateConversationPreview]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // 定时刷新
  useEffect(() => {
    const interval = setInterval(loadConversations, 30000);
    return () => clearInterval(interval);
  }, [loadConversations]);

  // 当前选中的用户组
  const selectedGroup = selectedUserId
    ? userGroups.find((g) => g.userId === selectedUserId) || null
    : null;

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
            onClick={loadConversations}
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

      {/* 主内容区：左右分栏 */}
      <main className="flex flex-1 overflow-hidden">
        {/* 左侧：用户列表 */}
        <aside className="w-80 flex-shrink-0 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 overflow-auto">
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
        <section className="flex-1 bg-zinc-50 dark:bg-zinc-950 overflow-hidden">
          <ConversationPanel group={selectedGroup} />
        </section>
      </main>
    </div>
  );
}
