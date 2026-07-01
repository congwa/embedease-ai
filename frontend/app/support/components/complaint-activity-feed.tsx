/**
 * 客诉实时活动流组件
 *
 * 这个文件的业务职责，是把当前主问题单的最近任务、审查、转人工和状态变化
 * 汇总成倒序活动流，帮助人工客服在接手瞬间看懂“系统刚刚做了什么”。
 */

import { cn } from "@/lib/utils";
import type {
  RecentTaskStateSummary,
  ReviewStateSummary,
  TicketStateSummary,
} from "@/types/websocket";
import {
  getComplaintReviewStatusLabel,
  getComplaintTaskStatusLabel,
  getComplaintTaskTypeLabel,
  getComplaintTicketStatusLabel,
  type ComplaintFlowTone,
} from "@/lib/config/complaint-ticket-flow";

interface ComplaintActivityFeedProps {
  currentTicket: TicketStateSummary | null;
  reviewSummary: ReviewStateSummary | null;
  handoffReason: string | null;
  recentTasks: RecentTaskStateSummary[];
}

interface ComplaintActivityItem {
  id: string;
  title: string;
  description: string;
  time: string | null;
  badge?: string | null;
  tone: ComplaintFlowTone;
}

/**
 * 格式化时间文本。
 *
 * 这个方法服务于活动流卡片，让客服快速知道最近一条动作是何时发生的。
 */
function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "未记录";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * 计算活动流卡片样式。
 *
 * 这个方法服务于让客服从颜色上区分推进成功、待处理、风险阻塞等动作。
 */
function getToneClassName(tone: ComplaintFlowTone): string {
  if (tone === "success") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
  }
  if (tone === "warning") {
    return "border-amber-500/30 bg-amber-500/10 text-amber-200";
  }
  if (tone === "danger") {
    return "border-red-500/30 bg-red-500/10 text-red-200";
  }
  if (tone === "info") {
    return "border-blue-500/30 bg-blue-500/10 text-blue-200";
  }
  return "border-zinc-700 bg-zinc-900 text-zinc-300";
}

/**
 * 构建任务活动项。
 *
 * 这个方法服务于把 AI 任务执行链压缩成客服能快速浏览的最近动作列表。
 */
function buildTaskActivityItems(recentTasks: RecentTaskStateSummary[]): ComplaintActivityItem[] {
  return recentTasks.map((task) => ({
    id: task.id,
    title: `${getComplaintTaskTypeLabel(task.task_type)}任务`,
    description:
      task.business_summary ||
      task.goal ||
      task.failure_reason ||
      `${task.agent_tag} 正在推进当前问题单`,
    time: task.finished_at || task.started_at || task.created_at,
    badge: `${task.agent_tag} · ${getComplaintTaskStatusLabel(task.status)}`,
    tone:
      task.status === "done"
        ? "success"
        : task.status === "failed" || task.status === "blocked"
          ? "danger"
          : "warning",
  }));
}

/**
 * 构建审查活动项。
 *
 * 这个方法服务于把最近 review 结论加入活动流，让客服知道系统为什么放行、驳回或升级。
 */
function buildReviewActivityItem(reviewSummary: ReviewStateSummary | null): ComplaintActivityItem[] {
  if (!reviewSummary) {
    return [];
  }

  return [
    {
      id: `review-${reviewSummary.created_at ?? "latest"}`,
      title: `审查${getComplaintReviewStatusLabel(reviewSummary.status)}`,
      description:
        reviewSummary.reasons?.[0] ||
        (typeof reviewSummary.score === "number"
          ? `最近一次质量评分为 ${reviewSummary.score}`
          : "系统已更新最近一次审查结论"),
      time: reviewSummary.created_at ?? null,
      badge:
        typeof reviewSummary.score === "number"
          ? `评分 ${reviewSummary.score}`
          : reviewSummary.risk_level || null,
      tone:
        reviewSummary.status === "passed"
          ? "success"
          : reviewSummary.status === "rejected" || reviewSummary.status === "escalated"
            ? "danger"
            : "warning",
    },
  ];
}

/**
 * 构建主问题单状态活动项。
 *
 * 这个方法服务于把当前 ticket 的落点状态放进活动流，让客服立刻知道当前卡在哪一层。
 */
function buildTicketActivityItem(
  currentTicket: TicketStateSummary | null,
  handoffReason: string | null
): ComplaintActivityItem[] {
  if (!currentTicket) {
    return [];
  }

  return [
    {
      id: `ticket-${currentTicket.id}-${currentTicket.updated_at ?? "latest"}`,
      title: `主问题单${getComplaintTicketStatusLabel(currentTicket.status)}`,
      description:
        handoffReason ||
        currentTicket.handoff_reason ||
        currentTicket.primary_issue_tag ||
        "系统正在推进当前主问题单",
      time: currentTicket.updated_at ?? null,
      badge: currentTicket.current_agent_tag || null,
      tone:
        currentTicket.status === "resolved" || currentTicket.status === "closed"
          ? "success"
          : currentTicket.status === "blocked" || currentTicket.status === "rework_required"
            ? "danger"
            : currentTicket.status === "handoff_pending" || currentTicket.status === "handed_off"
              ? "warning"
              : "info",
    },
  ];
}

/**
 * 构建转人工活动项。
 *
 * 这个方法服务于把“系统为何要求人工介入”单独提炼出来，避免淹没在其他状态信息里。
 */
function buildHandoffActivityItem(handoffReason: string | null): ComplaintActivityItem[] {
  if (!handoffReason) {
    return [];
  }

  return [
    {
      id: `handoff-${handoffReason}`,
      title: "系统请求人工接手",
      description: handoffReason,
      time: null,
      badge: "待介入",
      tone: "warning",
    },
  ];
}

/**
 * 客诉实时活动流组件。
 *
 * 这个组件把当前工单最关键的最近动作按时间倒序展示，方便人工一眼判断接下来该做什么。
 */
export function ComplaintActivityFeed({
  currentTicket,
  reviewSummary,
  handoffReason,
  recentTasks,
}: ComplaintActivityFeedProps) {
  const activityItems = [
    ...buildTaskActivityItems(recentTasks),
    ...buildReviewActivityItem(reviewSummary),
    ...buildTicketActivityItem(currentTicket, handoffReason),
    ...buildHandoffActivityItem(handoffReason),
  ].sort((left, right) => {
    const leftTime = new Date(left.time || 0).getTime();
    const rightTime = new Date(right.time || 0).getTime();
    return rightTime - leftTime;
  });

  if (activityItems.length === 0) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-zinc-100">实时活动流</h3>
        <p className="text-xs text-zinc-500">按最近动作倒序查看系统刚刚推进到了哪里</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {activityItems.slice(0, 6).map((item) => (
          <article
            key={item.id}
            className={cn("rounded-2xl border p-3 transition-colors", getToneClassName(item.tone))}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-sm font-medium text-white">{item.title}</div>
                <div className="mt-1 text-xs text-white/75">{item.description}</div>
              </div>
              {item.badge && (
                <span className="rounded-full bg-black/20 px-2 py-1 text-[11px] text-white/80">
                  {item.badge}
                </span>
              )}
            </div>

            <div className="mt-3 text-[11px] text-white/60">{formatDateTime(item.time)}</div>
          </article>
        ))}
      </div>
    </section>
  );
}
