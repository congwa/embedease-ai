"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "@/types/conversation";
import { getConversation, streamChat, type StreamChatController } from "@/lib/api";
import type { ChatEvent, ImageAttachment } from "@/types/chat";
import {
  type TimelineState,
  type TimelineItem,
  type SupportEventItem,
  createInitialState,
  addUserMessage,
  startAssistantTurn,
  timelineReducer,
  clearTurn,
  endTurn,
  historyToTimeline,
} from "./use-timeline-reducer";
import { useUserWebSocket } from "./use-user-websocket";
import type { SupportMessage, ConversationState } from "@/types/websocket";

export type {
  TimelineItem,
  TimelineState,
  UserMessageItem,
  LLMCallClusterItem,
  ToolCallItem,
  LLMCallSubItem,
  ToolCallSubItem,
  ReasoningSubItem,
  ContentSubItem,
  ProductsSubItem,
  TodosSubItem,
  ContextSummarizedSubItem,
  ErrorItem,
  FinalItem,
  MemoryEventItem,
  SupportEventItem,
  ItemStatus,
  // 兼容旧类型
  ReasoningItem,
  ContentItem,
  ProductsItem,
  TodosItem,
  ContextSummarizedItem,
} from "./use-timeline-reducer";

export function useChat(
  userId: string | null,
  conversationId: string | null,
  onTitleUpdate?: (title: string) => void
) {
  const [timelineState, setTimelineState] = useState<TimelineState>(createInitialState);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isHumanMode, setIsHumanMode] = useState(false);

  const streamControllerRef = useRef<StreamChatController | null>(null);
  const isStreamingRef = useRef(false);

  // 处理 WebSocket 消息（客服消息）
  const handleWsMessage = useCallback((message: SupportMessage) => {
    console.log("[chat] 收到 WebSocket 消息:", message.role, message.content?.slice(0, 50));
    
    // 只处理人工客服消息
    if (message.role === "human_agent") {
      const item: SupportEventItem = {
        type: "support.event",
        id: `support:${message.id || crypto.randomUUID()}`,
        turnId: `support-turn-${Date.now()}`,
        eventType: "human_message",
        content: message.content,
        operator: message.operator,
        messageId: message.id,
        ts: Date.now(),
      };

      setTimelineState((prev) => ({
        ...prev,
        timeline: [...prev.timeline, item],
        indexById: { ...prev.indexById, [item.id]: prev.timeline.length },
      }));
    }
  }, []);

  // 处理状态变更（客服上线/下线）
  const handleStateChange = useCallback((state: ConversationState) => {
    console.log("[chat] 会话状态变更:", state.handoff_state);
    setIsHumanMode(state.handoff_state === "human");
    
    // 添加状态变更事件到时间线
    const eventType = state.handoff_state === "human" ? "handoff_started" : "handoff_ended";
    const item: SupportEventItem = {
      type: "support.event",
      id: `support:${eventType}-${Date.now()}`,
      turnId: `support-turn-${Date.now()}`,
      eventType,
      operator: state.operator,
      message: state.handoff_state === "human" 
        ? "客服已上线，正在为您服务" 
        : "人工客服已结束服务，您可以继续与智能助手对话",
      ts: Date.now(),
    };

    setTimelineState((prev) => ({
      ...prev,
      timeline: [...prev.timeline, item],
      indexById: { ...prev.indexById, [item.id]: prev.timeline.length },
    }));
  }, []);

  // 用户端 WebSocket 连接（始终启用，用于接收客服事件）
  const { 
    isConnected: isWsConnected,
    conversationState,
    agentTyping,
  } = useUserWebSocket({
    conversationId,
    userId,
    onMessage: handleWsMessage,
    onStateChange: handleStateChange,
    enabled: !!conversationId && !!userId,
  });

  // 加载会话消息
  const loadMessages = useCallback(async () => {
    if (!conversationId) {
      setTimelineState(createInitialState());
      setIsHumanMode(false);
      return;
    }

    // 使用 ref 检查流状态，避免依赖状态导致不必要的重新调用
    if (isStreamingRef.current) {
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
      
      // 检测会话是否处于人工模式（WebSocket 会自动同步状态，这里只作初始化）
      const isHuman = conversation.handoff_state === "human";
      setIsHumanMode(isHuman);
      console.log("[chat] 加载了", messages.length, "条消息, 人工模式:", isHuman, ", WS连接:", isWsConnected);
    } catch (err) {
      console.error("[chat] 加载消息失败:", err);
      setError("加载消息失败");
    } finally {
      setIsLoading(false);
    }
  }, [conversationId]);

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
    async (content: string, targetConversationId?: string, images?: ImageAttachment[]) => {
      const convId = targetConversationId || conversationId;

      // 允许纯图片消息（无文本）
      if (!userId || !convId || (!content.trim() && (!images || images.length === 0))) {
        return;
      }

      setError(null);

      // 添加用户消息（包含图片信息）
      const userMessageId = crypto.randomUUID();
      setTimelineState((prev) => addUserMessage(prev, userMessageId, content.trim(), images));

      // 开始 assistant turn
      const assistantTurnId = crypto.randomUUID();
      setTimelineState((prev) => startAssistantTurn(prev, assistantTurnId));

      try {
        const controller: StreamChatController = { abort: () => { } };
        streamControllerRef.current = controller;
        isStreamingRef.current = true;
        let loggedDeltaOnce = false;
        for await (const event of streamChat(
          {
            user_id: userId,
            conversation_id: convId,
            message: content.trim(),
            images,
          },
          controller
        )) {
          // frontend/hooks/use-chat.ts
          if (
            event.type !== "assistant.delta" &&
            event.type !== "assistant.reasoning.delta"
          ) {
            loggedDeltaOnce = false;
            console.log("[SSE Event]", event.type, JSON.stringify(event.payload));
          } else if (!loggedDeltaOnce) {
            console.log("[SSE Event]", event.type, "(delta streaming)");
            loggedDeltaOnce = true;
          }
          
          // 检测人工模式
          if (event.type === "meta.start") {
            const payload = event.payload as { mode?: string };
            if (payload.mode === "human") {
              console.log("[chat] 进入人工模式，启用订阅");
              setIsHumanMode(true);
            }
          }
          
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
        isStreamingRef.current = false;
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
    isHumanMode,
    isWsConnected,
    agentTyping,
    conversationState,
    sendMessage,
    clearMessages,
    refreshMessages: loadMessages,
    abortStream,
  };
}
