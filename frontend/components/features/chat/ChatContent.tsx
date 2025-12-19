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
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import type { TimelineItem } from "@/hooks/use-timeline-reducer";
import {
  TimelineLlmCallItem,
  TimelineToolCallItem,
  TimelineReasoningItem,
  TimelineContentItem,
  TimelineProductsItem,
  TimelineUserMessageItem,
  TimelineErrorItem,
} from "./timeline";

interface ChatContentProps {  
  title: string;
  timeline: TimelineItem[];
  isStreaming: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  onAbortStream: () => void;
}

export function ChatContent({
  title,
  timeline,
  isStreaming,
  error,
  onSendMessage,
  onAbortStream,
}: ChatContentProps) {
  const [prompt, setPrompt] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
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

  const renderTimelineItem = (item: TimelineItem, index: number) => {
    switch (item.type) {
      case "user.message":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-end"
          >
            <TimelineUserMessageItem item={item} />
          </Message>
        );

      case "llm.call":
        return (
          <div
            key={item.id}
            className="mx-auto w-full max-w-3xl px-6"
          >
            <TimelineLlmCallItem item={item} />
          </div>
        );

      case "tool.call":
        return (
          <div
            key={item.id}
            className="mx-auto w-full max-w-3xl px-6"
          >
            <TimelineToolCallItem item={item} />
          </div>
        );

      case "assistant.reasoning":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <div className="flex w-full flex-col gap-3">
              <TimelineReasoningItem item={item} isStreaming={isStreaming} />
            </div>
          </Message>
        );

      case "assistant.content":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <div className="flex w-full flex-col gap-3">
              <TimelineContentItem item={item} />
            </div>
          </Message>
        );

      case "assistant.products":
        return (
          <Message
            key={item.id}
            className="mx-auto flex w-full max-w-3xl flex-col gap-2 px-6 items-start"
          >
            <div className="flex w-full flex-col gap-3">
              <TimelineProductsItem item={item} />
            </div>
          </Message>
        );

      case "error":
        return (
          <div
            key={item.id}
            className="mx-auto w-full max-w-3xl px-6"
          >
            <TimelineErrorItem item={item} />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <main className="flex h-screen flex-col overflow-hidden">
      {/* 顶部栏 */}
      <header className="z-10 flex h-16 w-full shrink-0 items-center gap-2 border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
        <SidebarTrigger className="-ml-1" />
        <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {title || "新对话"}
        </div>
      </header>

      {/* 消息区域 */}
      <div ref={chatContainerRef} className="relative flex-1 overflow-y-auto">
        <ChatContainerRoot className="h-full">
          <ChatContainerContent className="space-y-3 px-5 py-12">
            {timeline.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-orange-500/10">
                  <span className="text-2xl">🛒</span>
                </div>
                <h2 className="mb-2 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                  商品推荐助手
                </h2>
                <p className="text-center text-sm text-zinc-500">
                  告诉我你想要什么，我来帮你找到最合适的商品
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {["推荐一款降噪耳机", "有什么好的跑步鞋", "想买一台破壁机"].map(
                    (suggestion) => (
                      <Button
                        key={suggestion}
                        variant="outline"
                        size="sm"
                        className="text-xs"
                        onClick={() => {
                          onSendMessage(suggestion);
                        }}
                        disabled={isStreaming}
                      >
                        {suggestion}
                      </Button>
                    )
                  )}
                </div>
              </div>
            )}

            {timeline.map((item, index) => renderTimelineItem(item, index))}
          </ChatContainerContent>

          <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
            <ScrollButton className="shadow-sm" />
          </div>
        </ChatContainerRoot>
      </div>

      {/* 输入区域 */}
      <div className="z-10 shrink-0 bg-white px-3 pb-3 dark:bg-zinc-900 md:px-5 md:pb-5">
        <div className="mx-auto max-w-3xl">
          {/* 错误提示 */}
          {error && isErrorVisible && (
            <div className="mb-3 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setDismissedError(error)}
                className="shrink-0 rounded p-1 hover:bg-red-100 dark:hover:bg-red-900/40"
                title="关闭错误提示"
                aria-label="关闭错误提示"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          <PromptInput
            isLoading={isStreaming}
            value={prompt}
            onValueChange={setPrompt}
            onSubmit={handleButtonClick}
            className="relative z-10 w-full rounded-3xl border border-zinc-200 bg-white p-0 pt-1 shadow-sm dark:border-zinc-700 dark:bg-zinc-800"
          >
            <div className="flex flex-col">
              <PromptInputTextarea
                placeholder="描述你想要的商品..."
                className="min-h-[44px] pl-4 pt-3 text-base leading-[1.3]"
              />

              <PromptInputActions className="mt-5 flex w-full items-center justify-end gap-2 px-3 pb-3">
                <Button
                  size="icon"
                  disabled={!isStreaming && !prompt.trim()}
                  onClick={handleButtonClick}
                  className={cn(
                    "h-9 w-9 rounded-full transition-colors",
                    isStreaming && "bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
                  )}
                  title={isStreaming ? "停止生成" : "发送消息"}
                >
                  {isStreaming ? (
                    <Square className="h-4 w-4" />
                  ) : (
                    <ArrowUp className="h-4 w-4" />
                  )}
                </Button>
              </PromptInputActions>
            </div>
          </PromptInput>
        </div>
      </div>
    </main>
  );
}
