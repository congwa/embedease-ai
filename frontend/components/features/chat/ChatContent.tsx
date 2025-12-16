"use client";

import { useRef, useState } from "react";
import { AlertCircle, ArrowUp, Square, X } from "lucide-react";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import {
  Message,
  MessageContent,
} from "@/components/prompt-kit/message";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/hooks/use-chat";
import { ProductCard } from "./ProductCard";

interface ChatContentProps {
  title: string;
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  onAbortStream: () => void;
}

export function ChatContent({
  title,
  messages,
  isStreaming,
  error,
  onSendMessage,
  onAbortStream,
}: ChatContentProps) {
  const [prompt, setPrompt] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isErrorVisible = Boolean(error) && dismissedError !== error;

  // 修改：处理发送或停止
  const handleButtonClick = () => {
    if (isStreaming) {
      // 当前正在流式输出，点击则停止
      onAbortStream();
    } else {
      // 当前未发送，点击则发送
      if (!prompt.trim()) return;
      onSendMessage(prompt.trim());
      setPrompt("");
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
          <ChatContainerContent className="space-y-0 px-5 py-12">
            {messages.length === 0 && (
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

            {messages.map((message, messageIndex) => {
              const isAssistant = message.role === "assistant";
              const messageKey = message.id || `${message.role}-${messageIndex}`;

              if (!message.id) {
                console.log("[chat] message.id 缺失，已使用 fallback key", {
                  messageIndex,
                  role: message.role,
                });
              }

              return (
                <Message
                  key={messageKey}
                  className={cn(
                    "mx-auto flex w-full max-w-3xl flex-col gap-2 px-6",
                    isAssistant ? "items-start" : "items-end"
                  )}
                >
                  {isAssistant ? (
                    <div className="flex w-full flex-col gap-3">
                      <MessageContent
                        className="prose flex-1 rounded-lg bg-transparent p-0 text-zinc-900 dark:text-zinc-100"
                        markdown
                      >
                        {message.content || (message.isStreaming ? "思考中..." : "")}
                      </MessageContent>
                      
                      {/* 商品卡片 */}
                      {message.products && message.products.length > 0 && (
                        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          {message.products.map((product, productIndex) => {
                            const productId =
                              typeof product.id === "string" && product.id ? product.id : null;
                            const productKey = productId ?? `${messageKey}-product-${productIndex}`;
                            if (!productId) {
                              console.log("[chat] product.id 缺失，已使用 fallback key", {
                                messageId: message.id,
                                messageIndex,
                                productIndex,
                              });
                            }
                            return <ProductCard key={productKey} product={product} />;
                          })}
                        </div>
                      )}
                    </div>
                  ) : (
                    <MessageContent className="max-w-[85%] rounded-3xl bg-zinc-100 px-5 py-2.5 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 sm:max-w-[75%]">
                      {message.content}
                    </MessageContent>
                  )}
                </Message>
              );
            })}
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
