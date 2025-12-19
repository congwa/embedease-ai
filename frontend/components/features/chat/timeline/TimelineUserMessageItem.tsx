"use client";

import { MessageContent } from "@/components/prompt-kit/message";
import type { UserMessageItem } from "@/hooks/use-timeline-reducer";

interface TimelineUserMessageItemProps {
  item: UserMessageItem;
}

export function TimelineUserMessageItem({ item }: TimelineUserMessageItemProps) {
  return (
    <MessageContent className="max-w-[85%] rounded-3xl bg-zinc-100 px-5 py-2.5 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 sm:max-w-[75%]">
      {item.content}
    </MessageContent>
  );
}
