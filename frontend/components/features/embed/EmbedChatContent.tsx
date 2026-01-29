"use client";

import { useRef, useState } from "react";
import { AlertCircle, ArrowUp, Square, X } from "lucide-react";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import { Message } from "@/components/prompt-kit/message";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { ChatRichInput } from "@/components/features/chat/ChatRichInput";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TimelineItem } from "@/hooks/use-timeline-reducer";
import {
  LLMCallCluster,
  TimelineUserMessageItem,
  TimelineErrorItem,
  TimelineToolCallItem,
  TimelineSupportEventItem,
} from "@/components/features/chat/timeline";

interface SuggestedQuestionItem {
  id: string;
  question: string;
}

interface SuggestedQuestions {
  welcome: SuggestedQuestionItem[];
  input: SuggestedQuestionItem[];
}

interface EmbedChatContentProps {
  timeline: TimelineItem[];
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  onAbortStream: () => void;
  suggestedQuestions?: SuggestedQuestions;
  onSuggestionClick?: (question: string, id: string) => void;
}

const DEFAULT_SUGGESTIONS: SuggestedQuestionItem[] = [
  { id: "1", question: "推荐降噪耳机" },
  { id: "2", question: "好的跑步鞋" },
  { id: "3", question: "买破壁机" },
];

export function EmbedChatContent({
  timeline,
  isStreaming,
  isLoading,
  error,
  onSendMessage,
  onAbortStream,
  suggestedQuestions,
  onSuggestionClick,
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

      case "tool.call":
        return (
          <Message
            key={item.id}
            className="flex w-full flex-col gap-1 items-start px-3"
          >
            <TimelineToolCallItem item={item} />
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
        return null;

      case "support.event":
        return (
          <Message
            key={item.id}
            className="flex w-full flex-col gap-1 items-start px-3"
          >
            <TimelineSupportEventItem item={item} />
          </Message>
        );

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
                  {(suggestedQuestions?.welcome.length
                    ? suggestedQuestions.welcome
                    : DEFAULT_SUGGESTIONS
                  ).map((item) => (
                    <Button
                      key={item.id}
                      variant="outline"
                      size="sm"
                      className="text-xs h-7 px-2"
                      onClick={() => {
                        onSuggestionClick?.(item.question, item.id);
                        onSendMessage(item.question);
                      }}
                      disabled={isStreaming}
                    >
                      {item.question}
                    </Button>
                  ))}
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
        {/* 快捷问题栏 */}
        {suggestedQuestions && suggestedQuestions.input.length > 0 && (
          <div className="flex gap-1.5 overflow-x-auto pb-2 mb-2 scrollbar-thin">
            {suggestedQuestions.input.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  onSuggestionClick?.(item.question, item.id);
                  onSendMessage(item.question);
                }}
                disabled={isStreaming}
                className="shrink-0 px-2 py-1 text-xs rounded-full border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-orange-300 hover:bg-orange-50 dark:hover:border-orange-600 dark:hover:bg-orange-900/20 transition-colors whitespace-nowrap disabled:opacity-50"
              >
                {item.question}
              </button>
            ))}
          </div>
        )}
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
        <ChatRichInput
          value={prompt}
          onValueChange={setPrompt}
          onSubmit={handleButtonClick}
          placeholder="输入消息..."
          disabled={false}
          isLoading={isStreaming}
        />
      </div>
    </div>
  );
}
