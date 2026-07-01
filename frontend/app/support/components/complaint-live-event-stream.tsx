/**
 * 客诉实时事件流组件
 *
 * 这个文件的业务职责，是把客服页当前拿到的最新 ticket、review、任务和转人工快照
 * 即时转换成一组可读事件，让人工不用推断字段含义就能理解系统此刻正在发生什么。
 */

"use client";

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

interface ComplaintLiveEventStreamProps {
  conversationId: string;
  currentTicket: TicketStateSummary | null;
  reviewSummary: ReviewStateSummary | null;
  recentTasks: RecentTaskStateSummary[];
  handoffReason: string | null;
  handoffState: "ai" | "pending" | "human";
}

interface ComplaintLiveEvent {
  id: string;
  title: string;
  description: string;
  createdAt: string | null;
  tone: ComplaintFlowTone;
  badge?: string | null;
}

/**
 * 格式化时间文本。
 *
 * 这个方法服务于实时事件流，让客服快速知道某次动作大致发生在什么时候。
 */
function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "刚刚";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * 根据事件语义返回样式。
 *
 * 这个方法服务于人工一眼分辨推进成功、等待处理和风险阻塞类型的变化。
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
 * 构建主问题单事件。
 *
 * 这个方法服务于把当前主线问题的状态、归并和次级诉求识别信号直接翻译成事件。
 */
function buildTicketEvents(currentTicket: TicketStateSummary | null): ComplaintLiveEvent[] {
  if (!currentTicket) {
    return [];
  }

  const events: ComplaintLiveEvent[] = [
    {
      id: `ticket-status-${currentTicket.id}`,
      title: `主问题单${getComplaintTicketStatusLabel(currentTicket.status)}`,
      description:
        currentTicket.primary_issue_tag ||
        "系统已识别当前主问题单并继续推进处理。",
      createdAt: currentTicket.updated_at ?? null,
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

  if (currentTicket.merged_from_latest_message) {
    events.push({
      id: `ticket-merge-${currentTicket.id}`,
      title: "用户补充已归并到当前主单",
      description: "系统判断用户仍在围绕同一问题继续沟通，没有新建重复问题单。",
      createdAt: currentTicket.updated_at ?? null,
      badge: currentTicket.id.slice(0, 8),
      tone: "info",
    });
  }

  if (currentTicket.secondary_issue_detected) {
    events.push({
      id: `ticket-secondary-${currentTicket.id}`,
      title: "识别到次级诉求",
      description: "当前消息里出现了附带问题，系统已记录到主问题单上下文。",
      createdAt: currentTicket.updated_at ?? null,
      badge: currentTicket.primary_issue_tag || null,
      tone: "warning",
    });
  }

  return events;
}

/**
 * 构建最近任务事件。
 *
 * 这个方法服务于把 AI 岗位的推进任务转换成客服可直接理解的执行动作。
 */
function buildTaskEvents(recentTasks: RecentTaskStateSummary[]): ComplaintLiveEvent[] {
  return recentTasks.slice(0, 6).map((task) => ({
    id: task.id,
    title: `${getComplaintTaskTypeLabel(task.task_type)}任务${getComplaintTaskStatusLabel(task.status)}`,
    description:
      task.failure_reason ||
      task.business_summary ||
      task.goal ||
      `${task.agent_tag} 正在推进当前问题。`,
    createdAt: task.finished_at || task.started_at || task.created_at || null,
    badge: task.agent_tag,
    tone:
      task.status === "done"
        ? "success"
        : task.status === "failed" || task.status === "blocked"
          ? "danger"
          : "warning",
  }));
}

/**
 * 构建审查事件。
 *
 * 这个方法服务于把 review 结果转成“通过 / 驳回 / 升级人工”的可读事件。
 */
function buildReviewEvents(reviewSummary: ReviewStateSummary | null): ComplaintLiveEvent[] {
  if (!reviewSummary) {
    return [];
  }

  return [
    {
      id: `review-${reviewSummary.created_at ?? reviewSummary.status}`,
      title: `审查${getComplaintReviewStatusLabel(reviewSummary.status)}`,
      description:
        reviewSummary.reasons?.[0] ||
        (typeof reviewSummary.score === "number"
          ? `最近一次质量评分 ${reviewSummary.score}`
          : "系统已更新最近一次审查结果。"),
      createdAt: reviewSummary.created_at ?? null,
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
 * 构建转人工与服务模式事件。
 *
 * 这个方法服务于让客服看到当前是否处于 AI、待接入或人工模式，以及为什么需要人工。
 */
function buildServiceEvents(
  handoffReason: string | null,
  handoffState: "ai" | "pending" | "human",
  currentTicket: TicketStateSummary | null
): ComplaintLiveEvent[] {
  const events: ComplaintLiveEvent[] = [
    {
      id: `mode-${handoffState}`,
      title:
        handoffState === "human"
          ? "当前处于人工模式"
          : handoffState === "pending"
            ? "当前处于待人工接入"
            : "当前由 AI 持续跟进",
      description:
        handoffState === "human"
          ? "客服已正式接管此会话。"
          : handoffState === "pending"
            ? "系统已请求人工继续处理当前问题。"
            : "当前主问题仍由 AI 流程持续推进。",
      createdAt: currentTicket?.updated_at ?? null,
      badge: handoffState,
      tone: handoffState === "human" ? "success" : handoffState === "pending" ? "warning" : "info",
    },
  ];

  if (handoffReason) {
    events.push({
      id: `handoff-reason-${handoffReason}`,
      title: "系统请求人工接手",
      description: handoffReason,
      createdAt: currentTicket?.updated_at ?? null,
      badge: "待介入",
      tone: "warning",
    });
  }

  return events;
}

/**
 * 客诉实时事件流组件。
 *
 * 这个组件直接基于最新 support 快照渲染当前事件视图，避免客服漏看 ticket、review 或 handoff 变化。
 */
export function ComplaintLiveEventStream({
  conversationId,
  currentTicket,
  reviewSummary,
  recentTasks,
  handoffReason,
  handoffState,
}: ComplaintLiveEventStreamProps) {
  const events = [
    ...buildTicketEvents(currentTicket),
    ...buildTaskEvents(recentTasks),
    ...buildReviewEvents(reviewSummary),
    ...buildServiceEvents(handoffReason, handoffState, currentTicket),
  ]
    .sort((left, right) => {
      const leftTime = new Date(left.createdAt || 0).getTime();
      const rightTime = new Date(right.createdAt || 0).getTime();
      return rightTime - leftTime;
    })
    .slice(0, 9);

  if (events.length === 0) {
    return null;
  }

  return (
    <div className="border-b border-zinc-800 bg-zinc-950/50 px-4 py-3">
      <div className="mx-auto max-w-5xl">
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-zinc-100">实时事件流</h3>
          <p className="text-xs text-zinc-500">
            会话 {conversationId.slice(0, 8)} 当前最新的投诉推进动作
          </p>
        </div>

        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          {events.map((event) => (
            <article
              key={event.id}
              className={cn("rounded-2xl border p-3 transition-colors", getToneClassName(event.tone))}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-white">{event.title}</div>
                  <div className="mt-1 text-xs text-white/75">{event.description}</div>
                </div>
                {event.badge && (
                  <span className="rounded-full bg-black/20 px-2 py-1 text-[11px] text-white/80">
                    {event.badge}
                  </span>
                )}
              </div>

              <div className="mt-3 text-[11px] text-white/60">{formatDateTime(event.createdAt)}</div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
