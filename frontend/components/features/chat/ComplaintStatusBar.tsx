"use client";

import { CheckCircle2, ClipboardList, Headphones, Loader2, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ComplaintEventItem } from "@/lib/timeline/types";

/**
 * 当前处理阶段定义。
 *
 * 此结构用于把 complaint 事件序列映射到一条线性阶段进度，
 * 让用户一眼看出问题单目前处于哪个步骤。
 */
type ComplaintStage =
  | "identified"   // 已识别问题
  | "planning"     // 规划中
  | "processing"   // 处理中
  | "reviewing"    // 审查中
  | "handoff"      // 等待人工
  | "resolved";    // 已解决

const STAGES: { id: ComplaintStage; label: string }[] = [
  { id: "identified", label: "已识别" },
  { id: "processing", label: "处理中" },
  { id: "reviewing", label: "审查中" },
  { id: "resolved", label: "已解决" },
];

/**
 * 根据最新客诉事件列表推断当前处理阶段。
 *
 * 此函数服务于阶段进度条的渲染，按事件从后往前扫描，
 * 找到最近一条能决定阶段的事件后立即返回。
 */
function inferStage(events: ComplaintEventItem[]): ComplaintStage | null {
  if (events.length === 0) return null;
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.eventType === "handoff_requested") return "handoff";
    if (e.eventType === "review_passed") return "resolved";
    if (e.eventType === "review_rejected") return "processing";
    if (e.eventType === "review_pending") return "reviewing";
    if (e.eventType === "task_started" || e.eventType === "task_created") return "processing";
    if (e.eventType === "ticket_created" || e.eventType === "ticket_merged") return "identified";
  }
  return "identified";
}

/**
 * 从最新客诉事件中提取问题标签。
 *
 * 优先取 ticket.created 事件中的 primary_issue_tag，
 * 以便状态栏显示具体问题类型而不是泛化描述。
 */
function inferIssueTag(events: ComplaintEventItem[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (e.eventType === "ticket_created" || e.eventType === "ticket_merged") {
      if (e.description && e.description !== "系统已开始围绕当前问题单推进处理") {
        return e.description;
      }
    }
  }
  return null;
}

interface ComplaintStatusBarProps {
  complaintEvents: ComplaintEventItem[];
  className?: string;
}

/**
 * 客诉处理阶段状态栏（用户侧）。
 *
 * 此组件服务于用户侧聊天页的问题单进度可视化：当用户的问题进入
 * 正式客诉处理链后，在聊天顶部显示一条紧凑状态条，说明当前问题
 * 正处于哪个阶段，避免用户只看到 AI 回复而不知道问题已被记录和处理。
 */
export function ComplaintStatusBar({ complaintEvents, className }: ComplaintStatusBarProps) {
  const stage = inferStage(complaintEvents);
  const issueTag = inferIssueTag(complaintEvents);

  if (!stage) return null;

  // 转人工状态独立渲染
  if (stage === "handoff") {
    return (
      <div className={cn(
        "flex items-center gap-2 border-b bg-amber-50 px-4 py-2 text-xs text-amber-700 dark:bg-amber-950/30 dark:border-amber-900/30 dark:text-amber-300",
        className
      )}>
        <Headphones className="h-3.5 w-3.5 shrink-0" />
        <span className="font-medium">已转人工客服</span>
        {issueTag && (
          <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-amber-600 dark:bg-amber-900/40 dark:text-amber-400">
            {issueTag}
          </span>
        )}
        <span className="ml-auto text-amber-600/70 dark:text-amber-400/70">客服接手后将直接处理您的问题</span>
      </div>
    );
  }

  const currentStageIndex = STAGES.findIndex((s) => s.id === stage);

  return (
    <div className={cn(
      "flex items-center gap-3 border-b bg-blue-50/60 px-4 py-2 text-xs dark:bg-blue-950/20 dark:border-blue-900/30",
      className
    )}>
      <ClipboardList className="h-3.5 w-3.5 shrink-0 text-blue-500 dark:text-blue-400" />

      {/* 问题标签 */}
      {issueTag && (
        <span className="rounded bg-blue-100 px-1.5 py-0.5 font-medium text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
          {issueTag}
        </span>
      )}

      {/* 阶段进度条 */}
      <div className="flex items-center gap-1">
        {STAGES.map((s, idx) => {
          const isPast = idx < currentStageIndex;
          const isCurrent = idx === currentStageIndex;
          const isFuture = idx > currentStageIndex;
          return (
            <div key={s.id} className="flex items-center gap-1">
              {idx > 0 && (
                <div className={cn(
                  "h-px w-4",
                  isPast || isCurrent ? "bg-blue-400 dark:bg-blue-500" : "bg-zinc-200 dark:bg-zinc-700"
                )} />
              )}
              <div className={cn(
                "flex items-center gap-1 rounded px-1.5 py-0.5",
                isCurrent && "bg-blue-100 text-blue-700 font-medium dark:bg-blue-900/50 dark:text-blue-300",
                isPast && "text-blue-500 dark:text-blue-400",
                isFuture && "text-zinc-400 dark:text-zinc-600",
              )}>
                {isCurrent && stage !== "resolved" ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : isPast || stage === "resolved" ? (
                  <CheckCircle2 className="h-3 w-3" />
                ) : null}
                <span>{s.label}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 审查驳回提示 */}
      {complaintEvents.at(-1)?.eventType === "review_rejected" && (
        <span className="ml-auto flex items-center gap-1 text-amber-600 dark:text-amber-400">
          <AlertTriangle className="h-3 w-3" />
          正在优化回复
        </span>
      )}
    </div>
  );
}
