"use client";

import { MessageContent } from "@/components/prompt-kit/message";
import type { ContentItem } from "@/hooks/use-timeline-reducer";

interface TimelineContentItemProps {
  item: ContentItem;
}

export function TimelineContentItem({ item }: TimelineContentItemProps) {
  if (!item.text) return null;

  return (
    <MessageContent
      className="prose flex-1 rounded-lg bg-transparent p-0 text-zinc-900 dark:text-zinc-100"
      markdown
    >
      {item.text}
    </MessageContent>
  );
}
