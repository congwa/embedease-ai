"use client";

import { Loader2, Check, XCircle, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolCallItem, ItemStatus } from "@/hooks/use-timeline-reducer";

interface TimelineToolCallItemProps {
  item: ToolCallItem;
}

const STATUS_CONFIG: Record<
  ItemStatus,
  { icon: React.ReactNode; className: string }
> = {
  running: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    className: "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
  },
  success: {
    icon: <Check className="h-4 w-4" />,
    className: "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
  },
  error: {
    icon: <XCircle className="h-4 w-4" />,
    className: "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
  },
  empty: {
    icon: <Check className="h-4 w-4 opacity-60" />,
    className: "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
  },
};

function getStatusText(item: ToolCallItem): string {
  switch (item.status) {
    case "running":
      return `${item.label}中…`;
    case "success":
      return `${item.label}完成`;
    case "error":
      return `${item.label}失败`;
    case "empty":
      return `${item.label}无结果`;
    default:
      return item.label;
  }
}

export function TimelineToolCallItem({ item }: TimelineToolCallItemProps) {
  const config = STATUS_CONFIG[item.status];
  const showStats = item.status !== "running";

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-all",
        config.className
      )}
    >
      <Wrench className="h-4 w-4 opacity-60" />
      {config.icon}
      <span className="font-medium">{getStatusText(item)}</span>
      {showStats && item.count !== undefined && (
        <span className="text-xs opacity-70">· {item.count}项</span>
      )}
      {showStats && item.elapsedMs !== undefined && (
        <span className="text-xs opacity-70">· {item.elapsedMs}ms</span>
      )}
      {item.error && (
        <span className="text-xs opacity-70">· {item.error}</span>
      )}
    </div>
  );
}
