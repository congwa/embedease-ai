"use client";

import { useCallback, useMemo } from "react";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { useUser } from "@/hooks/use-user";
import { useConversations } from "@/hooks/use-conversations";
import { useChat } from "@/hooks/use-chat";
import { ChatSidebar } from "./ChatSidebar";
import { ChatContent } from "./ChatContent";

export function ChatApp() {
  // 用户状态
  const { userId, isLoading: isUserLoading } = useUser();

  // 会话状态
  const {
    conversations,
    currentConversationId,
    createNewConversation,
    removeConversation,
    selectConversation,
    updateConversationTitle,
  } = useConversations(userId);

  // 当前会话标题
  const currentConversation = useMemo(
    () => conversations.find((c) => c.id === currentConversationId),
    [conversations, currentConversationId]
  );

  // 标题更新回调
  const handleTitleUpdate = useCallback(
    (title: string) => {
      if (currentConversationId) {
        updateConversationTitle(currentConversationId, title);
      }
    },
    [currentConversationId, updateConversationTitle]
  );

  // 聊天状态（使用新的时间线 reducer）
  const { timeline, isStreaming, error, sendMessage, abortStream } = useChat(
    userId,
    currentConversationId,
    handleTitleUpdate
  );

  // 新建聊天
  const handleNewChat = useCallback(async () => {
    await createNewConversation();
  }, [createNewConversation]);

  // 发送消息（自动创建会话）
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!userId) return;
      
      let conversationId = currentConversationId;
      
      // 如果没有会话，先创建
      if (!conversationId) {
        const conversation = await createNewConversation();
        if (!conversation) return;
        conversationId = conversation.id;
      }
      
      // 使用指定的 conversationId 发送消息
      sendMessage(content, conversationId);
    },
    [userId, currentConversationId, createNewConversation, sendMessage]
  );

  // 加载中状态
  if (isUserLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-orange-500 border-t-transparent mx-auto" />
          <p className="text-sm text-zinc-500">正在加载...</p>
        </div>
      </div>
    );
  }

  return (
    <SidebarProvider>
      <ChatSidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={selectConversation}
        onDeleteConversation={removeConversation}
      />
      <SidebarInset>
        <ChatContent
          title={currentConversation?.title || ""}
          timeline={timeline}
          isStreaming={isStreaming}
          error={error}
          onSendMessage={handleSendMessage}
          onAbortStream={abortStream}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}
