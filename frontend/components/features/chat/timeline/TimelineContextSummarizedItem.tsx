"use client";

import { FileArchive, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ContextSummarizedItem } from "@/hooks/use-timeline-reducer";

interface TimelineContextSummarizedItemProps {
  item: ContextSummarizedItem;
}

export function TimelineContextSummarizedItem({
  item,
}: TimelineContextSummarizedItemProps) {
  const messagesReduced = item.messagesBefore - item.messagesAfter;
  const reductionPercent = Math.round(
    (messagesReduced / item.messagesBefore) * 100
  );

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm",
        "bg-amber-50 text-amber-700 border-amber-200",
        "dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800"
      )}
    >
      <FileArchive className="h-4 w-4 opacity-60" />
      <span className="font-medium">上下文已压缩</span>
      <span className="flex items-center gap-1 text-xs opacity-70">
        {item.messagesBefore} 条
        <ArrowRight className="h-3 w-3" />
        {item.messagesAfter} 条
      </span>
      <span className="text-xs opacity-60">(-{reductionPercent}%)</span>
      {item.tokensBefore !== undefined && item.tokensAfter !== undefined && (
        <span className="text-xs opacity-60">
          · {item.tokensBefore} → {item.tokensAfter} tokens
        </span>
      )}
    </div>
  );
}
