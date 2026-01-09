"use client";

import { cn } from "@/lib/utils";
import type { UserMessageItem } from "@/hooks/use-timeline-reducer";
import { useChatThemeOptional } from "../themes";
import { ImageGallery } from "./ImageGallery";

interface TimelineUserMessageItemProps {
  item: UserMessageItem;
}

export function TimelineUserMessageItem({ item }: TimelineUserMessageItemProps) {
  const theme = useChatThemeOptional();
  const themeId = theme?.themeId || "default";
  
  const hasImages = item.images && item.images.length > 0;
  const hasContent = item.content && item.content.trim().length > 0;
  
  return (
    <div 
      className={cn(
        "max-w-[85%] sm:max-w-[75%] rounded-lg p-2 text-foreground prose break-words whitespace-normal",
        themeId === "default" && "rounded-3xl bg-zinc-100 px-5 py-2.5 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100",
        themeId === "ethereal" && "chat-ethereal-user-msg",
        themeId === "industrial" && "chat-industrial-user-msg"
      )}
    >
      {hasImages && <ImageGallery images={item.images!} className="mb-2" />}
      {hasContent && <span>{item.content}</span>}
    </div>
  );
}
