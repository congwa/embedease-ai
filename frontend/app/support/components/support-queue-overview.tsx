/**
 * 客服队列总览组件
 *
 * 这个文件的业务职责，是把“全局待处理压力”和“当前筛选结果”拆开显示给人工客服，
 * 避免客服切换过滤条件后误解整个客诉系统的真实负载。
 */

"use client";

import {
  AlertTriangle,
  Flame,
  Headphones,
  Inbox,
  MessageSquareWarning,
  Radio,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { SupportStats } from "@/lib/api/support";
import type {
  ConversationWithPreview,
  UserConversationGroup,
} from "@/stores/support-workbench-store";

interface SupportQueueOverviewProps {
  stats: SupportStats | null;
  conversations: ConversationWithPreview[];
  userGroups: UserConversationGroup[];
  filter: string | null;
}

interface QueueMetric {
  label: string;
  value: number;
  description: string;
  tone: string;
  icon: LucideIcon;
}

/**
 * 生成当前筛选结果下的队列摘要。
 *
 * 这个方法服务于工作台总览区，帮助客服在当前过滤结果内继续判断是“风险高”还是“返工多”。
 */
function buildLoadedQueueMetrics(
  conversations: ConversationWithPreview[],
  userGroups: UserConversationGroup[]
): QueueMetric[] {
  const activeComplaintCount = conversations.filter(
    (conversation) =>
      conversation.ticket_status &&
      conversation.ticket_status !== "resolved" &&
      conversation.ticket_status !== "closed"
  ).length;
  const highRiskCount = conversations.filter(
    (conversation) => conversation.risk_level === "high"
  ).length;
  const reworkCount = conversations.filter(
    (conversation) =>
      conversation.review_status === "rejected" ||
      conversation.ticket_status === "rework_required" ||
      conversation.ticket_status === "blocked"
  ).length;
  const onlineUserCount = userGroups.filter((group) => group.hasOnlineUser).length;

  return [
    {
      label: "当前用户",
      value: userGroups.length,
      description: "当前筛选结果里的用户组数量",
      tone: "bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100",
      icon: Users,
    },
    {
      label: "活跃客诉",
      value: activeComplaintCount,
      description: "仍在推进中的问题单数量",
      tone: "bg-white text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100",
      icon: MessageSquareWarning,
    },
    {
      label: "高风险",
      value: highRiskCount,
      description: "已标记高风险的会话数量",
      tone: "bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300",
      icon: AlertTriangle,
    },
    {
      label: "返工/阻塞",
      value: reworkCount,
      description: "审查驳回或流程阻塞的会话数量",
      tone: "bg-orange-50 text-orange-700 dark:bg-orange-950/30 dark:text-orange-300",
      icon: Radio,
    },
    {
      label: "在线用户",
      value: onlineUserCount,
      description: "当前仍在线、适合优先处理的用户组",
      tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300",
      icon: Inbox,
    },
  ];
}

/**
 * 把过滤值翻译成客服看得懂的标签。
 *
 * 这个方法服务于总览提示文案，让客服知道当前看到的是全量队列还是某个子队列。
 */
function getFilterLabel(filter: string | null): string {
  if (filter === "pending") return "等待接入";
  if (filter === "human") return "人工处理中";
  if (filter === "ai") return "AI 处理中";
  return "全部会话";
}

/**
 * 客服队列总览组件。
 *
 * 这个组件承载列表页的第一层判断信息，让人工先看清全局压力，再进入下方具体用户和会话。
 */
export function SupportQueueOverview({
  stats,
  conversations,
  userGroups,
  filter,
}: SupportQueueOverviewProps) {
  const globalMetrics: QueueMetric[] = [
    {
      label: "待接入",
      value: stats?.pending_count ?? 0,
      description: "全局待人工接入会话数",
      tone: "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300",
      icon: Headphones,
    },
    {
      label: "人工处理中",
      value: stats?.human_count ?? 0,
      description: "全局人工客服正在跟进的会话数",
      tone: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300",
      icon: Users,
    },
    {
      label: "未读消息",
      value: stats?.total_unread ?? 0,
      description: "全局尚未被人工处理的新消息数",
      tone: "bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300",
      icon: Inbox,
    },
    {
      label: "高热会话",
      value: stats?.high_heat_count ?? 0,
      description: "全局热度较高的会话数",
      tone: "bg-orange-50 text-orange-700 dark:bg-orange-950/30 dark:text-orange-300",
      icon: Flame,
    },
  ];

  const loadedMetrics = buildLoadedQueueMetrics(conversations, userGroups);

  return (
    <section className="border-b border-zinc-200 bg-zinc-50 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
            队列总览
          </h2>
          <p className="text-xs text-zinc-500">
            当前筛选：{getFilterLabel(filter)}。上排为全局统计，下排为当前筛选结果快照。
          </p>
        </div>
      </div>

      <div className="grid gap-2 md:grid-cols-4">
        {globalMetrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.label}
              className={`rounded-2xl border border-zinc-200/70 px-3 py-3 shadow-sm dark:border-zinc-800 ${metric.tone}`}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="text-xs font-medium opacity-80">{metric.label}</span>
                <Icon className="h-4 w-4 opacity-80" />
              </div>
              <div className="text-2xl font-semibold">{metric.value}</div>
              <p className="mt-1 text-[11px] opacity-75">{metric.description}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-2 grid gap-2 md:grid-cols-5">
        {loadedMetrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.label}
              className={`rounded-2xl border border-zinc-200/70 px-3 py-3 shadow-sm dark:border-zinc-800 ${metric.tone}`}
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="text-xs font-medium opacity-80">{metric.label}</span>
                <Icon className="h-4 w-4 opacity-80" />
              </div>
              <div className="text-xl font-semibold">{metric.value}</div>
              <p className="mt-1 text-[11px] opacity-75">{metric.description}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
