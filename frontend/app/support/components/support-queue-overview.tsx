"use client";

/** Compact metrics keep global queue pressure separate from the currently loaded search results. */
import { Flame, Headphones, Inbox, UsersRound } from "lucide-react";
import type { SupportStats } from "@/lib/api/support";
import type {
  ConversationWithPreview,
  UserConversationGroup,
} from "@/stores/support-workbench-store";

interface SupportQueueOverviewProps {
  stats: SupportStats | null;
  conversations: ConversationWithPreview[];
  userGroups: UserConversationGroup[];
  mode: "global" | "filtered";
  onFilter?: (value: "pending" | "human" | "unread" | "hot") => void;
}

/** Both placements use the same source contract; global unknown values remain unknown until loaded. */
export function SupportQueueOverview({
  stats,
  conversations,
  userGroups,
  mode,
  onFilter,
}: SupportQueueOverviewProps) {
  if (mode === "global") {
    const metrics = [
      {
        key: "pending",
        label: "待接入",
        value: stats?.pending_count,
        icon: Headphones,
        warm: true,
      },
      {
        key: "human",
        label: "人工处理中",
        value: stats?.human_count,
        icon: UsersRound,
      },
      {
        key: "unread",
        label: "未读消息",
        value: stats?.total_unread,
        icon: Inbox,
      },
      {
        key: "hot",
        label: "高热会话",
        value: stats?.high_heat_count,
        icon: Flame,
        warm: true,
      },
    ] as const;
    return (
      <section
        aria-label="全局队列统计"
        className="support-global-metrics grid shrink-0 grid-cols-4 gap-2 px-1 pt-1 pb-5 md:gap-5 md:px-4 md:pb-6"
      >
        {metrics.map(({ key, label, value, icon: Icon, ...metric }) => (
          <button
            key={key}
            onClick={() => onFilter?.(key)}
            aria-label={`${label} ${value ?? "加载中"}，查看队列`}
            className="flex min-w-0 items-center gap-3 rounded-2xl py-2 text-left transition-colors hover:bg-secondary md:px-1"
          >
            <span
              className={`hidden size-10 shrink-0 items-center justify-center rounded-2xl md:flex ${"warm" in metric && metric.warm ? "support-warning" : "bg-secondary text-muted-foreground"}`}
            >
              <Icon aria-hidden="true" className="size-4" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[11px] text-muted-foreground sm:text-xs">
                {label}
              </span>
              <span className="mt-1 block text-xl font-semibold tabular-nums md:text-2xl">
                {value === undefined ? "—" : String(value).padStart(2, "0")}
              </span>
            </span>
          </button>
        ))}
      </section>
    );
  }
  const metrics = [
    ["用户", userGroups.length, "当前用户组数量"],
    [
      "活跃",
      conversations.filter(
        (c) =>
          c.ticket_status && !["resolved", "closed"].includes(c.ticket_status),
      ).length,
      "仍在推进的客诉数量",
    ],
    [
      "高风险",
      conversations.filter((c) => c.risk_level === "high").length,
      "已标记高风险的会话数量",
    ],
    [
      "返工",
      conversations.filter(
        (c) =>
          c.review_status === "rejected" ||
          ["rework_required", "blocked"].includes(c.ticket_status ?? ""),
      ).length,
      "审查驳回或流程阻塞的会话数量",
    ],
    [
      "在线",
      userGroups.filter((g) => g.hasOnlineUser).length,
      "当前在线用户组数量",
    ],
  ] as const;
  return (
    <footer className="support-queue-footer shrink-0 border-t border-border px-5 py-4">
      <div className="mb-3 flex justify-between text-[11px] text-muted-foreground">
        <span>当前筛选结果</span>
        <span>已加载会话</span>
      </div>
      <dl className="grid grid-cols-5 gap-2">
        {metrics.map(([label, value, description]) => (
          <div key={label} title={description}>
            <dt className="text-[11px] text-muted-foreground">
              {label}
              <span className="sr-only">：{description}</span>
            </dt>
            <dd className="-order-1 mb-1 text-sm font-medium tabular-nums">
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </footer>
  );
}
