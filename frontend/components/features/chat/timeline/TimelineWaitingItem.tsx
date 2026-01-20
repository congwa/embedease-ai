"use client";

import { Loader2 } from "lucide-react";
import type { WaitingItem } from "@/lib/timeline-utils";

interface TimelineWaitingItemProps {
  item: WaitingItem;
}

export function TimelineWaitingItem({ item }: TimelineWaitingItemProps) {
  return (
    <div className="flex items-center gap-2 text-zinc-500 text-sm py-2">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>正在连接...</span>
    </div>
  );
}
