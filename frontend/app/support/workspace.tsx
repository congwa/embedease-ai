"use client";

/** Persistent support shell keeps queue, global pressure and real-time subscriptions available while switching chats. */
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  AudioLines,
  Inbox,
  BookOpen,
  LayoutGrid,
  RefreshCw,
  Search,
  X,
  SlidersHorizontal,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { getSupportConversations, getSupportStats } from "@/lib/api/support";
import { buildSupportWorkbenchMonitoredConversations } from "@/lib/config/support-workbench-monitoring";
import { useSupportWorkbenchStore } from "@/stores";
import { useSupportWorkbenchRealtime } from "@/hooks/use-support-workbench-realtime";
import { UserList } from "./components/user-list";
import { SupportQueueOverview } from "./components/support-queue-overview";

/** Uses real queue data; search narrows loaded conversations without changing the independent global stats. */
export default function SupportWorkspace({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const activeId = pathname.split("/")[2] ?? null;
  const [query, setQuery] = useState("");
  const [special, setSpecial] = useState<"unread" | "hot" | null>(null);

  // 使用 Store 管理状态
  const {
    conversations,
    userGroups,
    stats,
    filter,
    sortBy,
    isLoading,
    error,
    setConversations,
    setStats,
    setFilter,
    setSortBy,
    setLoading,
    setError,
    patchConversation,
  } = useSupportWorkbenchStore();

  // 初始化状态：防止首次渲染闪烁
  const [isInitialized, setIsInitialized] = useState(false);

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
  const queueRequest = useRef(0);
  const loadConversations = useCallback(
    async (silent = false) => {
      const request = ++queueRequest.current;
      try {
        if (!silent) setLoading(true);
        setError(null);
        const convData = await getSupportConversations(
          filter || undefined,
          sortBy,
        );
        if (request !== queueRequest.current) return;
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
          })),
        );
      } catch (e) {
        if (request === queueRequest.current)
          setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        if (request === queueRequest.current) setLoading(false);
      }
    },
    [filter, sortBy, setConversations, setLoading, setError],
  );

  /**
   * 同步刷新工作台主数据。
   *
   * 这个方法服务于首次进入和人工手动刷新场景，确保列表数据和顶部统计一起校准。
   */
  const loadWorkbench = useCallback(
    async (silent = false) => {
      await Promise.all([loadConversations(silent), loadStats()]);
    },
    [loadConversations, loadStats],
  );

  // The persistent shell reloads only the queue when filters change; the active chat stays mounted.
  useEffect(() => {
    void loadWorkbench().finally(() => setIsInitialized(true));
  }, [loadWorkbench]);

  // 定时静默刷新（不显示 loading）
  useEffect(() => {
    if (!isInitialized) return;
    const interval = setInterval(() => {
      void loadWorkbench(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [isInitialized, loadWorkbench]);

  // 当前选中的用户组
  const selectedGroup =
    userGroups.find((group) =>
      group.conversations.some((conversation) => conversation.id === activeId),
    ) ?? null;

  /**
   * 按实时事件粒度刷新列表或统计。
   *
   * 这个方法服务于列表页实时闭环：能本地补丁更新的先补丁，只有影响过滤结果或全局统计时
   * 才补拉接口，避免每条事件都整页重载。
   */
  const handleRealtimeSignal = useCallback(
    (_: string, action: string) => {
      const shouldReloadConversations =
        action === "server.support_queue_changed" ||
        (filter !== null &&
          (action === "server.conversation_state" ||
            action === "server.handoff_started" ||
            action === "server.handoff_ended"));
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
    },
    [filter, loadConversations, loadStats],
  );

  const monitoredConversations = buildSupportWorkbenchMonitoredConversations(
    conversations,
    selectedGroup?.conversations ?? [],
  );

  useSupportWorkbenchRealtime({
    // The detail route already owns the active conversation socket.
    conversations: monitoredConversations.filter(
      (conversation) => conversation.id !== activeId,
    ),
    agentId,
    enabled: isInitialized,
    onPatchConversation: patchConversation,
    onSignal: handleRealtimeSignal,
  });

  const normalizedQuery = query.trim().toLocaleLowerCase();
  const visibleGroups = userGroups
    .map((group) => ({
      ...group,
      conversations: group.conversations.filter(
        (conversation) =>
          (!special ||
            (special === "unread"
              ? conversation.unread_count > 0 &&
                ["pending", "human"].includes(conversation.handoff_state)
              : conversation.heat_score > 60)) &&
          (!normalizedQuery ||
            [
              group.userId,
              conversation.id,
              conversation.title,
              conversation.lastMessage,
              conversation.primary_issue_tag,
            ].some((value) =>
              value?.toLocaleLowerCase().includes(normalizedQuery),
            )),
      ),
    }))
    .filter((group) => group.conversations.length > 0);
  const visibleConversations = visibleGroups.flatMap(
    (group) => group.conversations,
  );
  const filteredGroups = visibleGroups.map((group) => ({
    ...group,
    hasOnlineUser: group.conversations.some(
      (conversation) => conversation.user_online,
    ),
  }));

  return (
    <div className="support-theme dark flex h-dvh overflow-hidden bg-background text-foreground">
      <a className="support-skip" href="#support-content">
        跳到会话工作区
      </a>
      <nav
        aria-label="产品导航"
        className="hidden w-[76px] shrink-0 flex-col items-center gap-5 py-5 md:flex"
      >
        <Link
          href="/support"
          aria-label="EmbedEase 客服工作台"
          className="mb-7 flex size-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground"
        >
          <AudioLines className="size-5" />
        </Link>
        <Link
          href="/admin"
          title="管理概览"
          aria-label="管理概览"
          className="support-rail-link"
        >
          <LayoutGrid className="size-5" />
        </Link>
        <Link
          href="/support"
          title="会话工作台"
          aria-label="会话工作台"
          aria-current="page"
          className="support-rail-link bg-accent text-foreground"
        >
          <Inbox className="size-5" />
        </Link>
        <Link
          href="/admin/knowledge"
          title="知识库"
          aria-label="知识库"
          className="support-rail-link"
        >
          <BookOpen className="size-5" />
        </Link>
        <span
          className="mt-auto flex size-9 items-center justify-center rounded-full bg-secondary text-xs"
          title="当前客服"
        >
          客
        </span>
      </nav>
      <div className="flex min-w-0 flex-1 flex-col px-3 pb-3 md:pr-5 md:pl-1 md:pb-5">
        <header className="support-main-header flex h-20 shrink-0 items-center justify-between gap-3 px-1 md:px-4">
          <div>
            <p className="mb-1 hidden text-xs text-muted-foreground sm:block">
              工作空间 <span className="mx-2">/</span> 客户服务
            </p>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold tracking-tight md:text-2xl">
                客服工作台
              </h1>
              <span className="support-badge support-success hidden sm:inline-flex">
                服务进行中
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-muted-foreground lg:block">
              {conversations.length} 个会话 · {userGroups.length} 位客户
            </span>
            <Button
              variant="ghost"
              size="icon"
              aria-label="刷新客服队列"
              disabled={isLoading}
              onClick={() => void loadWorkbench()}
            >
              <RefreshCw
                className={cn(
                  "size-4",
                  isLoading && "animate-spin motion-reduce:animate-none",
                )}
              />
            </Button>
          </div>
        </header>
        <SupportQueueOverview
          mode="global"
          stats={stats}
          conversations={conversations}
          userGroups={userGroups}
          onFilter={(value) => {
            setFilter(value === "pending" || value === "human" ? value : null);
            setSpecial(value === "unread" || value === "hot" ? value : null);
            router.push("/support");
          }}
        />
        <div className="flex min-h-0 flex-1 overflow-hidden rounded-[24px] border border-border bg-card">
          <aside
            aria-label="会话队列"
            className={cn(
              "flex w-full shrink-0 flex-col border-r border-border md:w-[280px] 2xl:w-[336px]",
              activeId && "hidden md:flex",
            )}
          >
            <div className="space-y-4 px-5 pt-6 pb-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold">
                  会话收件箱{" "}
                  <span className="ml-1 rounded bg-secondary px-1.5 py-0.5 text-xs text-muted-foreground">
                    {conversations.length}
                  </span>
                </h2>
                <SlidersHorizontal
                  aria-hidden="true"
                  className="size-4 text-muted-foreground"
                />
              </div>
              <div className="relative">
                <Search
                  aria-hidden="true"
                  className="pointer-events-none absolute top-3 left-3 size-4 text-muted-foreground"
                />
                <Input
                  aria-label="搜索客户、会话或消息"
                  placeholder="搜索客户、会话或消息"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  className="h-10 rounded-xl pr-9 pl-9 text-sm"
                />
                {query && (
                  <Button
                    className="absolute top-1 right-1 size-8"
                    variant="ghost"
                    size="icon"
                    aria-label="清除搜索"
                    onClick={() => setQuery("")}
                  >
                    <X className="size-3.5" />
                  </Button>
                )}
              </div>
              <div className="flex gap-1" aria-label="会话状态筛选">
                {(
                  [
                    [null, "全部"],
                    ["pending", "待接入"],
                    ["human", "人工"],
                    ["ai", "AI"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={label}
                    aria-pressed={filter === value && !special}
                    onClick={() => {
                      setFilter(value);
                      setSpecial(null);
                    }}
                    className={cn(
                      "support-filter",
                      filter === value && !special && "is-selected",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
                <span>
                  {visibleConversations.length} 个会话
                  {special ? ` · ${special === "hot" ? "高热" : "未读"}` : ""}
                </span>
                <select
                  aria-label="会话排序"
                  className="min-h-8 bg-transparent text-xs text-muted-foreground outline-offset-4"
                  value={sortBy}
                  onChange={(event) =>
                    setSortBy(event.target.value as "heat" | "time")
                  }
                >
                  <option value="heat">优先处理</option>
                  <option value="time">最新消息</option>
                </select>
              </div>
            </div>
            {error && (
              <div
                role="alert"
                className="mx-4 mb-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
              >
                <AlertCircle className="mr-1 inline size-4" />
                {error}
                <button
                  className="ml-2 underline"
                  onClick={() => void loadWorkbench()}
                >
                  重试
                </button>
              </div>
            )}
            <div
              className="min-h-0 flex-1 overflow-y-auto px-2 pb-3"
              aria-busy={isLoading}
            >
              {!isInitialized ? (
                <div className="space-y-3 p-3" aria-label="正在加载队列">
                  {[1, 2, 3].map((key) => (
                    <div
                      key={key}
                      className="h-24 animate-pulse rounded-2xl bg-muted motion-reduce:animate-none"
                    />
                  ))}
                </div>
              ) : visibleGroups.length ? (
                <UserList
                  groups={filteredGroups}
                  activeConversationId={activeId}
                  onSelectConversation={(id) =>
                    router.push(`/support/${encodeURIComponent(id)}`)
                  }
                />
              ) : (
                <div className="flex h-full min-h-40 flex-col items-center justify-center gap-3 px-3 text-center text-sm text-muted-foreground">
                  <Search className="size-6" />
                  <p>
                    {normalizedQuery || special
                      ? "没有匹配的会话"
                      : "当前队列暂无会话"}
                  </p>
                  {(normalizedQuery || special) && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setQuery("");
                        setSpecial(null);
                      }}
                    >
                      清除筛选
                    </Button>
                  )}
                </div>
              )}
            </div>
            <SupportQueueOverview
              mode="filtered"
              stats={stats}
              conversations={visibleConversations}
              userGroups={filteredGroups}
            />
          </aside>
          <main
            id="support-content"
            tabIndex={-1}
            className={cn(
              "min-w-0 flex-1 overflow-hidden bg-background",
              !activeId && "hidden md:block",
            )}
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
