"use client";

import { useState } from "react";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/prompt-kit/reasoning";
import type { ReasoningItem } from "@/hooks/use-timeline-reducer";

interface TimelineReasoningItemProps {
  item: ReasoningItem;
  isStreaming?: boolean;
}

export function TimelineReasoningItem({
  item,
  isStreaming,
}: TimelineReasoningItemProps) {
  const [isOpen, setIsOpen] = useState(item.isOpen);

  // 如果 item.isOpen 变化（比如 final 时关闭），同步更新
  // 但不覆盖用户手动操作
  const effectiveOpen = isOpen;

  return (
    <Reasoning
      isStreaming={isStreaming}
      open={effectiveOpen}
      onOpenChange={setIsOpen}
    >
      <ReasoningTrigger>推理过程</ReasoningTrigger>
      <ReasoningContent className="mt-2" markdown>
        {item.text}
      </ReasoningContent>
    </Reasoning>
  );
}
