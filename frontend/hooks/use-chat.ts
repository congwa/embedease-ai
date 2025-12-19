"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "@/types/conversation";
import { getConversation, streamChat, type StreamChatController } from "@/lib/api";
import type { ChatEvent } from "@/types/chat";
import {
  type TimelineState,
  type TimelineItem,
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  timelineReducer,
  clearTurn,
  endTurn,
  historyToTimeline,
} from "./use-timeline-reducer";

export type {
  TimelineItem,
  TimelineState,
  UserMessageItem,
  LlmCallItem,
  ReasoningItem,
  ContentItem,
  ToolCallItem,
  ProductsItem,
  ErrorItem,
  ItemStatus,
} from "./use-timeline-reducer";

export function useChat(
  userId: string | null,
  conversationId: string | null,
  onTitleUpdate?: (title: string) => void
) {
  const [timelineState, setTimelineState] = useState<TimelineState>(createInitialState);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const streamControllerRef = useRef<StreamChatController | null>(null);

  // 加载会话消息
  const loadMessages = useCallback(async () => {
    if (!conversationId) {
      setTimelineState(createInitialState());
      return;
    }

    if (timelineState.activeTurn.isStreaming) {
      console.log("[chat] 正在流式传输，跳过加载");
      return;
    }

    setIsLoading(true);
    try {
      const conversation = await getConversation(conversationId);
      const messages = conversation.messages.map((msg: Message) => ({
        id: msg.id,
        role: msg.role as "user" | "assistant",
        content: msg.content,
        products: msg.products ? JSON.parse(msg.products) : undefined,
      }));
      setTimelineState(historyToTimeline(messages));
      console.log("[chat] 加载了", messages.length, "条消息");
    } catch (err) {
      console.error("[chat] 加载消息失败:", err);
      setError("加载消息失败");
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, timelineState.activeTurn.isStreaming]);

  // 中断当前对话
  const abortStream = useCallback(() => {
    if (streamControllerRef.current) {
      console.log("[chat] 用户中断对话");
      streamControllerRef.current.abort();
      streamControllerRef.current = null;

      // 清除当前 turn 的所有 items
      const currentTurnId = timelineState.activeTurn.turnId;
      if (currentTurnId) {
        setTimelineState((prev) => clearTurn(prev, currentTurnId));
      }
    }
  }, [timelineState.activeTurn.turnId]);

  // 发送消息
  const sendMessage = useCallback(
    async (content: string, targetConversationId?: string) => {
      const convId = targetConversationId || conversationId;

      if (!userId || !convId || !content.trim()) {
        return;
      }

      setError(null);

      // 添加用户消息
      const userMessageId = crypto.randomUUID();
      setTimelineState((prev) => addUserMessage(prev, userMessageId, content.trim()));

      // 开始 assistant turn
      const assistantTurnId = crypto.randomUUID();
      setTimelineState((prev) => startAssistantTurn(prev, assistantTurnId));

      try {
        const controller: StreamChatController = { abort: () => {} };
        streamControllerRef.current = controller;

        for await (const event of streamChat(
          {
            user_id: userId,
            conversation_id: convId,
            message: content.trim(),
          },
          controller
        )) {
          console.log("[SSE Event]", event.type, JSON.stringify(event.payload));
          setTimelineState((prev) => timelineReducer(prev, event));
        }

        // 流结束
        setTimelineState((prev) => endTurn(prev));

        // 更新会话标题
        if (timelineState.timeline.length === 0 && onTitleUpdate) {
          const title = content.slice(0, 50) + (content.length > 50 ? "..." : "");
          onTitleUpdate(title);
        }
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
          // 清除当前 turn
          setTimelineState((prev) => clearTurn(prev, assistantTurnId));
        }
      } finally {
        streamControllerRef.current = null;
      }
    },
    [userId, conversationId, timelineState.timeline.length, onTitleUpdate]
  );

  // 清空消息
  const clearMessages = useCallback(() => {
    setTimelineState(createInitialState());
    setError(null);
  }, []);

  // 当会话 ID 变化时重新加载消息
  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  return {
    timeline: timelineState.timeline,
    isStreaming: timelineState.activeTurn.isStreaming,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    refreshMessages: loadMessages,
    abortStream,
  };
}
