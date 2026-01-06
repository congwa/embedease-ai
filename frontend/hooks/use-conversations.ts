"use client";

import { useCallback, useEffect, useState } from "react";
import type { Conversation } from "@/types/conversation";
import { getUserConversations, createConversation, deleteConversation } from "@/lib/api";

export function useConversations(userId: string | null) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // 加载会话列表
  const loadConversations = useCallback(async () => {
    if (!userId) return;
    
    setIsLoading(true);
    try {
      const data = await getUserConversations(userId);
      setConversations(data);
      console.log("[conversations] 加载了", data.length, "个会话");
    } catch (error) {
      console.error("[conversations] 加载失败:", error);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  // 创建新会话
  const createNewConversation = useCallback(async (): Promise<Conversation | null> => {
    if (!userId) return null;
    
    try {
      const conversation = await createConversation({ user_id: userId });
      setConversations((prev) => [conversation, ...prev]);
      setCurrentConversationId(conversation.id);
      console.log("[conversations] 创建新会话:", conversation.id);
      return conversation;
    } catch (error) {
      console.error("[conversations] 创建失败:", error);
      return null;
    }
  }, [userId]);

  // 删除会话
  const removeConversation = useCallback(async (conversationId: string) => {
    try {
      await deleteConversation(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
      
      if (currentConversationId === conversationId) {
        setCurrentConversationId(null);
      }
      
      console.log("[conversations] 删除会话:", conversationId);
    } catch (error) {
      console.error("[conversations] 删除失败:", error);
    }
  }, [currentConversationId]);

  // 选择会话
  const selectConversation = useCallback((conversationId: string) => {
    setCurrentConversationId(conversationId);
    console.log("[conversations] 选择会话:", conversationId);
  }, []);

  // 更新会话标题
  const updateConversationTitle = useCallback(
    (conversationId: string, title: string) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId ? { ...c, title } : c
        )
      );
    },
    []
  );

  // 初始加载
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return {
    conversations,
    currentConversationId,
    isLoading,
    createNewConversation,
    removeConversation,
    selectConversation,
    updateConversationTitle,
    refreshConversations: loadConversations,
  };
}
