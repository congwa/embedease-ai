"use client";

import { useRef, useState } from "react";
import { AlertCircle, ArrowUp, Square, X } from "lucide-react";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import { Message } from "@/components/prompt-kit/message";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TimelineItem } from "@/hooks/use-timeline-reducer";
import {
  LLMCallCluster,
  TimelineUserMessageItem,
  TimelineErrorItem,
} from "../chat/timeline";

interface EmbedChatContentProps {
  timeline: TimelineItem[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  onAbortStream: () => void;
}

export function EmbedChatContent({
  timeline,
  isStreaming,
  isLoading,
  error,
  onSendMessage,
  onAbortStream,
}: EmbedChatContentProps) {
  const [prompt, setPrompt] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const isErrorVisible = Boolean(error) && dismissedError !== error;

  const handleButtonClick = () => {
    if (isStreaming) {
      onAbortStream();
    } else {
      if (!prompt.trim()) return;
      onSendMessage(prompt.trim());
      setPrompt("");
    }
  };

  const renderTimelineItem = (item: TimelineItem) => {
    switch (item.type) {
      case "user.message":
        return (
          <Message
            key={item.id}
            className="flex w-full flex-col gap-1 items-end px-3"
          >
            <TimelineUserMessageItem item={item} />
          </Message>
        );

      case "llm.call.cluster":
        return (
          <Message
            key={item.id}
            className="flex w-full flex-col gap-1 items-start px-3"
          >
            <LLMCallCluster item={item} isStreaming={isStreaming} />
          </Message>
        );

      case "error":
        return (
          <div key={item.id} className="w-full px-3">
            <TimelineErrorItem item={item} />
          </div>
        );

      case "final":
      case "memory.event":
      case "support.event":
        return null;

      default:
        return null;
    }
  };

  // 加载中状态
  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <div className="mb-2 h-6 w-6 animate-spin rounded-full border-2 border-orange-500 border-t-transparent mx-auto" />
          <p className="text-xs text-zinc-500">正在加载...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* 消息区域 */}
      <div className="relative flex-1 overflow-y-auto">
        <ChatContainerRoot className="h-full">
          <ChatContainerContent className="space-y-2 py-4">
            {timeline.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8 px-4">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-orange-500/10">
                  <span className="text-xl">🛒</span>
                </div>
                <h3 className="mb-1 text-sm font-medium text-zinc-900 dark:text-zinc-100">
                  有什么可以帮您？
                </h3>
                <p className="text-center text-xs text-zinc-500 mb-4">
                  告诉我你想要什么商品
                </p>
                <div className="flex flex-wrap justify-center gap-1.5">
                  {["推荐降噪耳机", "好的跑步鞋", "买破壁机"].map(
                    (suggestion) => (
                      <Button
                        key={suggestion}
                        variant="outline"
                        size="sm"
                        className="text-xs h-7 px-2"
                        onClick={() => onSendMessage(suggestion)}
                        disabled={isStreaming}
                      >
                        {suggestion}
                      </Button>
                    )
                  )}
                </div>
              </div>
            )}

            {timeline.map((item) => renderTimelineItem(item))}
          </ChatContainerContent>

          <div className="absolute bottom-2 right-3">
            <ScrollButton className="shadow-sm h-7 w-7" />
          </div>
        </ChatContainerRoot>
      </div>

      {/* 输入区域 */}
      <div className="shrink-0 border-t border-zinc-200 bg-white p-3 dark:border-zinc-700 dark:bg-zinc-900">
        {/* 错误提示 */}
        {error && isErrorVisible && (
          <div className="mb-2 flex items-center gap-2 rounded-lg bg-red-50 p-2 text-xs text-red-600 dark:bg-red-900/20 dark:text-red-400">
            <AlertCircle className="h-3 w-3 shrink-0" />
            <span className="flex-1 line-clamp-2">{error}</span>
            <button
              onClick={() => setDismissedError(error)}
              className="shrink-0 rounded p-0.5 hover:bg-red-100 dark:hover:bg-red-900/40"
              title="关闭"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
        <PromptInput
          isLoading={isStreaming}
          value={prompt}
          onValueChange={setPrompt}
          onSubmit={handleButtonClick}
          className="relative w-full rounded-2xl border border-zinc-200 bg-zinc-50 p-0 dark:border-zinc-700 dark:bg-zinc-800"
        >
          <div className="flex items-center gap-1 pr-1">
            <PromptInputTextarea
              placeholder="输入消息..."
              className="min-h-[36px] max-h-[100px] pl-3 py-2 text-sm leading-[1.4] flex-1"
            />
            <PromptInputActions className="flex items-center">
              <Button
                size="icon"
                disabled={!isStreaming && !prompt.trim()}
                onClick={handleButtonClick}
                className={cn(
                  "h-7 w-7 rounded-full transition-colors",
                  isStreaming &&
                    "bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
                )}
                title={isStreaming ? "停止" : "发送"}
              >
                {isStreaming ? (
                  <Square className="h-3 w-3" />
                ) : (
                  <ArrowUp className="h-3 w-3" />
                )}
              </Button>
            </PromptInputActions>
          </div>
        </PromptInput>
      </div>
    </div>
  );
}
