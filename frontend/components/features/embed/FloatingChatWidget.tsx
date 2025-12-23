"use client";

import { useState, useCallback } from "react";
import { MessageCircle, X, Trash2, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { EmbedChatContent } from "./EmbedChatContent";
import { useUser } from "@/hooks/use-user";
import { useChat } from "@/hooks/use-chat";
import { createConversation } from "@/lib/api";

interface FloatingChatWidgetProps {
  className?: string;
}

export function FloatingChatWidget({ className }: FloatingChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const { userId, isLoading: isUserLoading } = useUser();

  const { timeline, isStreaming, error, sendMessage, clearMessages, abortStream } =
    useChat(userId, conversationId);

  // 发送消息（自动创建会话）
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!userId) return;

      let convId = conversationId;

      // 如果没有会话，先创建
      if (!convId) {
        try {
          const conversation = await createConversation({ user_id: userId });
          convId = conversation.id;
          setConversationId(convId);
        } catch (err) {
          console.error("[embed] 创建会话失败:", err);
          return;
        }
      }

      sendMessage(content, convId);
    },
    [userId, conversationId, sendMessage]
  );

  // 清空对话（创建新会话）
  const handleClearChat = useCallback(async () => {
    if (!userId) return;

    // 如果正在流式传输，先中断
    if (isStreaming) {
      abortStream();
    }

    // 清空消息
    clearMessages();

    // 创建新会话
    try {
      const conversation = await createConversation({ user_id: userId });
      setConversationId(conversation.id);
      console.log("[embed] 创建新会话:", conversation.id);
    } catch (err) {
      console.error("[embed] 创建新会话失败:", err);
      setConversationId(null);
    }
  }, [userId, isStreaming, abortStream, clearMessages]);

  const toggleOpen = () => setIsOpen((prev) => !prev);

  return (
    <div className={cn("fixed bottom-4 right-4 z-50", className)}>
      {/* 聊天面板 */}
      {isOpen && (
        <div className="mb-4 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-2xl dark:border-zinc-700 dark:bg-zinc-900">
          {/* 头部 */}
          <div className="flex h-12 shrink-0 items-center justify-between border-b border-zinc-200 bg-zinc-50 px-4 dark:border-zinc-700 dark:bg-zinc-800">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-orange-500/10">
                <span className="text-sm">🛒</span>
              </div>
              <span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                商品推荐助手
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleClearChat}
                title="清空对话"
                disabled={isUserLoading}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={toggleOpen}
                title="收起"
              >
                <Minus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* 聊天内容 */}
          <EmbedChatContent
            timeline={timeline}
            isStreaming={isStreaming}
            isLoading={isUserLoading}
            error={error}
            onSendMessage={handleSendMessage}
            onAbortStream={abortStream}
          />
        </div>
      )}

      {/* 悬浮按钮 */}
      <Button
        onClick={toggleOpen}
        size="icon"
        className={cn(
          "h-14 w-14 rounded-full shadow-lg transition-all",
          isOpen
            ? "bg-zinc-600 hover:bg-zinc-700 dark:bg-zinc-700 dark:hover:bg-zinc-600"
            : "bg-orange-500 hover:bg-orange-600 dark:bg-orange-600 dark:hover:bg-orange-500"
        )}
      >
        {isOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <MessageCircle className="h-6 w-6" />
        )}
      </Button>
    </div>
  );
}
