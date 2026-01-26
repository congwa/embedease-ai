"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SkillActivatedItem } from "@/lib/timeline-utils";

interface TimelineSkillActivatedItemProps {
  item: SkillActivatedItem;
}

export function TimelineSkillActivatedItem({ item }: TimelineSkillActivatedItemProps) {
  return (
    <div className="flex justify-center py-2">
      <div
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1 rounded-full",
          "bg-purple-50 text-purple-700 text-xs font-medium",
          "dark:bg-purple-900/30 dark:text-purple-300",
          "border border-purple-200 dark:border-purple-800",
          "animate-in fade-in-0 zoom-in-95 duration-300"
        )}
      >
        <Sparkles className="h-3 w-3" />
        <span>已启用「{item.skillName}」技能</span>
        {item.triggerKeyword && (
          <span className="opacity-60">· 关键词: {item.triggerKeyword}</span>
        )}
      </div>
    </div>
  );
}
