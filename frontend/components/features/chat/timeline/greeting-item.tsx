"use client";

import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/prompt-kit/markdown";
import type { GreetingItem } from "@/hooks/use-timeline-reducer";

interface TimelineGreetingItemProps {
  item: GreetingItem;
  onCtaClick?: (payload: string) => void;
}

export function TimelineGreetingItem({ item, onCtaClick }: TimelineGreetingItemProps) {
  const handleCtaClick = () => {
    if (item.cta?.payload && onCtaClick) {
      onCtaClick(item.cta.payload);
    }
  };

  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
        <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2">
        <div className="rounded-lg bg-white p-3 shadow-sm dark:bg-zinc-800">
          {/* Title */}
          {item.title && (
            <h4 className="mb-1 font-semibold text-zinc-900 dark:text-zinc-100">
              {item.title}
            </h4>
          )}

          {/* Subtitle */}
          {item.subtitle && (
            <p className="mb-2 text-sm text-zinc-500">{item.subtitle}</p>
          )}

          {/* Body */}
          <Markdown className="prose prose-sm dark:prose-invert max-w-none">
            {item.body}
          </Markdown>

          {/* CTA Button */}
          {item.cta && item.cta.text && (
            <div className="mt-3 pt-2">
              <Button
                size="sm"
                onClick={handleCtaClick}
                className="bg-blue-600 text-white hover:bg-blue-700"
              >
                {item.cta.text}
              </Button>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="text-xs text-zinc-400">刚刚</div>
      </div>
    </div>
  );
}
