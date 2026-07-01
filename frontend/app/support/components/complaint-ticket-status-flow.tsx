/**
 * 客诉问题单状态流组件
 *
 * 这个文件的业务职责，是把 ticket 的阶段推进、任务执行、审查结果和当前状态
 * 折叠成一条客服可读的状态流，帮助人工快速判断系统已经推进到哪一步、卡在哪一步。
 */

import { cn } from "@/lib/utils";
import type { RecentTaskSummary, TicketDetail } from "@/lib/api/support";
import {
  getComplaintReviewStatusLabel,
  getComplaintTaskStatusLabel,
  getComplaintTaskTypeLabel,
  getComplaintTicketStatusLabel,
  getComplaintTimelineEventMeta,
  type ComplaintFlowTone,
} from "@/lib/config/complaint-ticket-flow";

interface ComplaintTicketStatusFlowProps {
  ticket: TicketDetail;
}

interface TicketFlowStep {
  id: string;
  title: string;
  description: string;
  time: string | null;
  tone: ComplaintFlowTone;
  badge?: string | null;
}

/**
 * 格式化时间文本。
 *
 * 这个方法服务于状态流节点，让客服快速判断某个阶段大概发生在什么时候。
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
 * 选择状态流节点的颜色语义。
 *
 * 这个方法服务于客服一眼区分通过、阻塞、人工接管和普通推进节点。
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
 * 生成任务节点说明。
 *
 * 这个方法服务于把任务目标、执行岗位和失败原因压缩成客服可读的一句话。
 */
function buildTaskDescription(task: RecentTaskSummary): string {
  if (task.failure_reason) {
    return task.failure_reason;
  }
  if (task.business_summary) {
    return task.business_summary;
  }
  if (task.goal) {
    return task.goal;
  }
  return `${task.agent_tag} 正在推进 ${getComplaintTaskTypeLabel(task.task_type)}`;
}

/**
 * 把业务时间线事件转换为状态流节点。
 *
 * 这个方法服务于保留后端沉淀的 ticket.timeline，让人工看到关键阶段是如何推进的。
 */
function buildTimelineSteps(ticket: TicketDetail): TicketFlowStep[] {
  const timelineEntries = [...ticket.timeline].sort((left, right) => {
    const leftTime = new Date(left.created_at || 0).getTime();
    const rightTime = new Date(right.created_at || 0).getTime();
    return leftTime - rightTime;
  });

  return timelineEntries.map((entry, index) => {
    const meta = getComplaintTimelineEventMeta(entry.event_type);

    return {
      id: `${entry.event_type}-${entry.created_at ?? index}`,
      title: meta.label,
      description: entry.summary || "系统已推进当前问题单",
      time: entry.created_at,
      tone: meta.tone,
      badge: null,
    };
  });
}

/**
 * 把近期任务摘要转换为状态流节点。
 *
 * 这个方法服务于让客服知道 AI 哪个岗位做过什么事，而不需要手动展开任务原始结构。
 */
function buildTaskSteps(ticket: TicketDetail): TicketFlowStep[] {
  return [...ticket.recent_tasks]
    .sort((left, right) => {
      const leftTime = new Date(left.created_at || left.started_at || 0).getTime();
      const rightTime = new Date(right.created_at || right.started_at || 0).getTime();
      return leftTime - rightTime;
    })
    .map((task) => ({
      id: task.id,
      title: `${getComplaintTaskTypeLabel(task.task_type)}任务`,
      description: buildTaskDescription(task),
      time: task.finished_at || task.started_at || task.created_at,
      tone:
        task.status === "done"
          ? "success"
          : task.status === "failed" || task.status === "blocked"
            ? "danger"
            : "warning",
      badge: `${task.agent_tag} · ${getComplaintTaskStatusLabel(task.status)}`,
    }));
}

/**
 * 生成当前问题单的审查和落点节点。
 *
 * 这个方法服务于客服判断当前是否已经审查通过、是否待人工接管，以及最终是否已解决。
 */
function buildDecisionSteps(ticket: TicketDetail): TicketFlowStep[] {
  const steps: TicketFlowStep[] = [];

  if (ticket.latest_review) {
    steps.push({
      id: `review-${ticket.latest_review.created_at ?? "latest"}`,
      title: `审查${getComplaintReviewStatusLabel(ticket.latest_review.status)}`,
      description:
        ticket.latest_review.reasons?.[0] ||
        (typeof ticket.latest_review.score === "number"
          ? `质量分 ${ticket.latest_review.score}`
          : "系统已产出最近一次审查结论"),
      time: ticket.latest_review.created_at,
      tone:
        ticket.latest_review.status === "passed"
          ? "success"
          : ticket.latest_review.status === "rejected"
            ? "danger"
            : "warning",
      badge:
        typeof ticket.latest_review.score === "number"
          ? `评分 ${ticket.latest_review.score}`
          : null,
    });
  }

  if (ticket.handoff_required || ticket.status === "handoff_pending" || ticket.status === "handed_off") {
    steps.push({
      id: `handoff-${ticket.updated_at ?? "latest"}`,
      title: ticket.status === "handed_off" ? "人工已接手" : "等待人工接管",
      description: ticket.handoff_reason || "系统判定需要人工介入当前问题",
      time: ticket.updated_at,
      tone: "warning",
      badge: ticket.current_agent_tag || null,
    });
  }

  steps.push({
    id: `status-${ticket.status}-${ticket.updated_at ?? "latest"}`,
    title: `当前状态：${getComplaintTicketStatusLabel(ticket.status)}`,
    description:
      ticket.resolved_summary ||
      ticket.handoff_reason ||
      ticket.current_node_key ||
      ticket.current_agent_tag ||
      "系统正在继续推进当前问题单",
    time: ticket.resolved_at || ticket.closed_at || ticket.updated_at,
    tone:
      ticket.status === "resolved" || ticket.status === "closed"
        ? "success"
        : ticket.status === "blocked" || ticket.status === "rework_required"
          ? "danger"
          : ticket.status === "handoff_pending" || ticket.status === "handed_off"
            ? "warning"
            : "info",
    badge: ticket.current_agent_tag || null,
  });

  return steps;
}

/**
 * 客诉问题单状态流组件。
 *
 * 这个组件把 ticket 的关键推进轨迹渲染成单列状态流，方便人工在几秒内判断当前单子所处阶段。
 */
export function ComplaintTicketStatusFlow({ ticket }: ComplaintTicketStatusFlowProps) {
  const steps: TicketFlowStep[] = [
    {
      id: `created-${ticket.id}`,
      title: "问题进入系统",
      description: ticket.primary_issue_tag || "系统已创建并开始处理当前问题单",
      time: ticket.created_at,
      tone: "info",
      badge: ticket.id.slice(0, 8),
    },
    ...buildTimelineSteps(ticket),
    ...buildTaskSteps(ticket),
    ...buildDecisionSteps(ticket),
  ];

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
      <div className="mb-3">
        <div className="text-[11px] uppercase tracking-wide text-zinc-500">状态流转</div>
        <div className="mt-1 text-sm text-zinc-300">
          从建单到当前状态，按真实业务推进轨迹展示
        </div>
      </div>

      <div className="space-y-3">
        {steps.map((step, index) => (
          <div key={step.id} className="relative pl-6">
            {index < steps.length - 1 && (
              <div className="absolute left-[9px] top-6 h-[calc(100%+12px)] w-px bg-zinc-800" />
            )}

            <div className={cn("absolute left-0 top-1 h-[18px] w-[18px] rounded-full border", getToneClassName(step.tone))} />

            <div className="space-y-2 rounded-2xl border border-zinc-800 bg-zinc-900/80 px-3 py-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-medium text-zinc-100">{step.title}</div>
                  <div className="mt-1 text-xs text-zinc-400">{step.description}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {step.badge && (
                    <span className={cn("rounded-full border px-2 py-1 text-[11px]", getToneClassName(step.tone))}>
                      {step.badge}
                    </span>
                  )}
                  <span className="text-[11px] text-zinc-500">{formatDateTime(step.time)}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
