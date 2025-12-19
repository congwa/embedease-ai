"use client";

import { Loader2, Check, XCircle, Brain } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LlmCallItem, ItemStatus } from "@/hooks/use-timeline-reducer";

interface TimelineLlmCallItemProps {
  item: LlmCallItem;
}

const STATUS_CONFIG: Record<
  ItemStatus,
  { icon: React.ReactNode; text: string; className: string }
> = {
  running: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    text: "模型思考中…",
    className: "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800",
  },
  success: {
    icon: <Check className="h-4 w-4" />,
    text: "思考完成",
    className: "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
  },
  error: {
    icon: <XCircle className="h-4 w-4" />,
    text: "思考失败",
    className: "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
  },
  empty: {
    icon: <Check className="h-4 w-4" />,
    text: "无结果",
    className: "bg-zinc-50 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
  },
};

export function TimelineLlmCallItem({ item }: TimelineLlmCallItemProps) {
  const config = STATUS_CONFIG[item.status];
  const showElapsed = item.status !== "running" && item.elapsedMs !== undefined;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-all",
        config.className
      )}
    >
      <Brain className="h-4 w-4 opacity-60" />
      {config.icon}
      <span className="font-medium">{config.text}</span>
      {showElapsed && (
        <span className="text-xs opacity-70">· {item.elapsedMs}ms</span>
      )}
      {item.error && (
        <span className="text-xs opacity-70">· {item.error}</span>
      )}
    </div>
  );
}
