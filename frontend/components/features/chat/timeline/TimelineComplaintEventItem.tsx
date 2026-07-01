"use client";

import { AlertTriangle, CheckCircle2, ClipboardList, Headphones, Ticket } from "lucide-react";
import type { ComplaintEventItem } from "@/hooks/use-timeline-reducer";
import { cn } from "@/lib/utils";

interface TimelineComplaintEventItemProps {
  item: ComplaintEventItem;
}

/**
 * 根据客诉事件类型选择图标。
 *
 * 这个函数用于让不同处理阶段在时间线上有稳定的视觉语义。
 */
function getComplaintIcon(eventType: ComplaintEventItem["eventType"]) {
  if (eventType === "review_passed") {
    return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />;
  }
  if (eventType === "review_rejected" || eventType === "blocked") {
    return <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />;
  }
  if (eventType === "handoff_requested") {
    return <Headphones className="mt-0.5 h-4 w-4 shrink-0" />;
  }
  if (eventType === "ticket_created" || eventType === "ticket_merged" || eventType === "secondary_issue_detected") {
    return <Ticket className="mt-0.5 h-4 w-4 shrink-0" />;
  }
  return <ClipboardList className="mt-0.5 h-4 w-4 shrink-0" />;
}

/**
 * 根据客诉事件类型选择色彩语义。
 *
 * 这个函数用于把通过、驳回、转人工等关键结果直接映射到稳定的提示色。
 */
function getComplaintTone(eventType: ComplaintEventItem["eventType"]) {
  if (eventType === "review_passed") {
    return "bg-green-50 text-green-700 dark:bg-green-950/30 dark:text-green-300";
  }
  if (eventType === "review_rejected" || eventType === "blocked") {
    return "bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300";
  }
  if (eventType === "handoff_requested") {
    return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300";
  }
  return "bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300";
}

/**
 * 渲染客诉编排事件卡片。
 *
 * 这个组件用于把 complaint.* 领域事件直接展示给用户，解释当前问题单正处在哪个处理阶段。
 */
export function TimelineComplaintEventItem({ item }: TimelineComplaintEventItemProps) {
  return (
    <div className="flex items-center justify-center py-2">
      <div className={cn("flex max-w-[85%] items-start gap-3 rounded-2xl px-4 py-3 text-sm", getComplaintTone(item.eventType))}>
        {getComplaintIcon(item.eventType)}
        <div className="space-y-1">
          <div className="font-medium">{item.label}</div>
          {item.description && (
            <div className="text-xs opacity-80">{item.description}</div>
          )}
        </div>
      </div>
    </div>
  );
}
