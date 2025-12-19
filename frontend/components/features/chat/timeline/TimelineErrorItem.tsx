"use client";

import { AlertCircle } from "lucide-react";
import type { ErrorItem } from "@/hooks/use-timeline-reducer";

interface TimelineErrorItemProps {
  item: ErrorItem;
}

export function TimelineErrorItem({ item }: TimelineErrorItemProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
      <AlertCircle className="h-4 w-4 shrink-0" />
      <span>{item.message}</span>
    </div>
  );
}
