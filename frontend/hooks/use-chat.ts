"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message } from "@/types/conversation";
import type { Product } from "@/types/product";
import { getConversation, streamChat, type StreamChatController } from "@/lib/api";
import type { ChatEvent, ToolStartPayload, ToolEndPayload, LlmCallStartPayload, LlmCallEndPayload } from "@/types/chat";

/** 工具名称中文映射（<=10字） */
const TOOL_LABEL_MAP: Record<string, string> = {
  search_products: "商品搜索",
  get_product_details: "商品详情",
  filter_by_price: "价格筛选",
  compare_products: "商品对比",
};

function getToolLabel(name: string): string {
  return TOOL_LABEL_MAP[name] || name.slice(0, 10);
}

/** 状态类型定义 */
export type LlmStatus = "running" | "success" | "error";
export type ToolStatus = "running" | "success" | "error";

/** 轨迹步骤（用于 TracePanel 展示） */
export type TraceStep =
  | {
      id: string;
      kind: "llm";
      status: LlmStatus;
      startedAt: number;
      endedAt?: number;
      elapsedMs?: number;
      error?: string;
      messageCount?: number;
    }
  | {
      id: string;
      kind: "tool";
      name: string;
      label: string;
      status: ToolStatus;
      startedAt: number;
      endedAt?: number;
      elapsedMs?: number;
      count?: number;
      error?: string;
    }
  | {
      id: string;
      kind: "products";
      count: number;
      ts: number;
    }
  | {
      id: string;
      kind: "error";
      message: string;
      ts: number;
    };

/** 工具摘要（用于标题右侧 badge） */
export interface ToolsSummary {
  runningCount: number;
  last?: {
    name: string;
    label: string;
    status: ToolStatus;
    elapsedMs?: number;
    count?: number;
    error?: string;
  };
}

/** LLM 摘要（用于标题右侧 badge，永久展示） */
export interface LlmSummary {
  status: LlmStatus;
  elapsedMs?: number;
  error?: string;
  messageCount?: number;
}

/** 消息 timeline item */
export interface MessageItem {
  type: "message";
  id: string;
  message: ChatMessage;
}

/** 时间轴 item（仅保留消息，不再插入 tool/llm） */
export type TimelineItem = MessageItem;

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning?: string;
  /**
   * 按时间顺序的分段内容（用于支持：推理 -> 正文 -> 推理 -> 正文 ... 交替显示）
   * - reasoning：推理片段（可折叠）
   * - content：真实回复片段（正常展示）
   */
  segments?: Array<{
    id: string;
    kind: "reasoning" | "content";
    text: string;
    /**
     * 仅对 reasoning 有意义：
     * - streaming 时当前推理段默认展开
     * - 一旦进入 content 段，上一段推理会自动折叠（但不会消失）
     */
    isOpen?: boolean;
  }>;
  products?: Product[];
  isStreaming?: boolean;
  
  /** LLM 调用状态（永久展示在推理标题右侧） */
  llm?: LlmSummary;
  /** 工具摘要（展示在推理标题右侧） */
  toolsSummary?: ToolsSummary;
  /** 运行轨迹（展示在 TracePanel 中） */
  trace?: TraceStep[];
  /** UI 状态 */
  ui?: { isTraceOpen?: boolean };
}

export function useChat(
  userId: string | null,
  conversationId: string | null,
  onTitleUpdate?: (title: string) => void
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isSending, setIsSending] = useState(false); // 标记正在发送消息
  const [error, setError] = useState<string | null>(null);
  
  // 保存当前流的控制器
  const streamControllerRef = useRef<StreamChatController | null>(null);
  // 工具调用栈（按 messageId 维度隔离，用于配对 tool.start/tool.end）
  const inFlightToolStackRef = useRef<Record<string, Record<string, string[]>>>({});

  // 加载会话消息
  const loadMessages = useCallback(async () => {
    if (!conversationId) {
      setMessages([]);
      setTimeline([]);
      return;
    }

    // 如果正在发送消息，跳过加载（避免清空刚添加的消息）
    if (isSending) {
      console.log("[chat] 正在发送消息，跳过加载");
      return;
    }

    setIsLoading(true);
    try {
      const conversation = await getConversation(conversationId);
      const chatMessages: ChatMessage[] = conversation.messages.map((msg: Message) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        segments:
          msg.role === "assistant" && msg.content
            ? [
                {
                  id: `${msg.id}-content-0`,
                  kind: "content" as const,
                  text: msg.content,
                },
              ]
            : undefined,
        products: msg.products ? JSON.parse(msg.products) : undefined,
      }));
      setMessages(chatMessages);
      // 历史消息转为 timeline（不含工具调用，因为历史不保存工具状态）
      const timelineItems: TimelineItem[] = chatMessages.map((msg) => ({
        type: "message" as const,
        id: msg.id,
        message: msg,
      }));
      setTimeline(timelineItems);
      console.log("[chat] 加载了", chatMessages.length, "条消息");
    } catch (error) {
      console.error("[chat] 加载消息失败:", error);
      setError("加载消息失败");
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, isSending]);

  // 中断当前对话
  const abortStream = useCallback(() => {
    if (streamControllerRef.current) {
      console.log("[chat] 用户中断对话");
      streamControllerRef.current.abort();
      streamControllerRef.current = null;
      
      // 移除最后一条正在生成的助手消息（因为后端不会保存被中断的消息）
      setMessages((prev) =>
        prev.filter((msg, index) => 
          !(index === prev.length - 1 && msg.role === "assistant" && msg.isStreaming)
        )
      );
      // 同步清理 timeline：移除正在流式的 assistant 消息
      setTimeline((prev) =>
        prev.filter((item) => {
          if (item.message.role === "assistant" && item.message.isStreaming) {
            return false;
          }
          return true;
        })
      );
      // 清理工具调用栈
      inFlightToolStackRef.current = {};
      
      setIsStreaming(false);
      setIsSending(false);
    }
  }, []);

  // 发送消息
  const sendMessage = useCallback(
    async (content: string, targetConversationId?: string) => {
      const convId = targetConversationId || conversationId;
      
      if (!userId || !convId || !content.trim()) {
        return;
      }

      setError(null);
      setIsSending(true); // 标记开始发送
      setIsStreaming(true);

      // 重置工具调用栈
      inFlightToolStackRef.current = {};

      // 添加用户消息
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: content.trim(),
      };
      setMessages((prev) => {
        return [...prev, userMessage];
      });
      // 同步到 timeline
      setTimeline((prev) => [
        ...prev,
        { type: "message", id: userMessage.id, message: userMessage },
      ]);

      // 添加空的助手消息（用于流式显示）
      let assistantMessageId = crypto.randomUUID();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        segments: [],
        isStreaming: true,
        llm: undefined,
        toolsSummary: { runningCount: 0 },
        trace: [],
        ui: { isTraceOpen: false },
      };
      // 初始化该消息的工具调用栈
      inFlightToolStackRef.current[assistantMessageId] = {};
      setMessages((prev) => {
        return [...prev, assistantMessage];
      });
      // 同步到 timeline
      setTimeline((prev) => [
        ...prev,
        { type: "message", id: assistantMessageId, message: assistantMessage },
      ]);

      let fullContent = "";
      let fullReasoning = "";
      let products: Product[] | undefined;

      const applyAssistantSegmentsDelta = (
        kind: "reasoning" | "content",
        delta: string,
        nextContent: string,
        nextReasoning: string
      ) => {
        // 关键：捕获当前 assistantMessageId，避免 setState updater 延迟执行时读取到被后续事件改写后的 id
        const targetId = assistantMessageId;

        // 复用同一套逻辑计算新 message
        const patchMessage = (msg: ChatMessage): ChatMessage => {
          const prevSegments = Array.isArray(msg.segments) ? msg.segments : [];
          const segments = [...prevSegments];
          const last = segments.length > 0 ? segments[segments.length - 1] : undefined;

          if (last && last.kind === kind) {
            segments[segments.length - 1] = { ...last, text: last.text + delta };
          } else {
            // 进入新段：如果上一个是推理段，自动折叠它（但不移除）
            if (last && last.kind === "reasoning") {
              segments[segments.length - 1] = { ...last, isOpen: false };
            }
            segments.push({
              id: crypto.randomUUID(),
              kind,
              text: delta,
              isOpen: kind === "reasoning",
            });

            console.log("[chat] segment switch", {
              from: last?.kind ?? null,
              to: kind,
              assistantMessageId,
              segmentsCount: segments.length,
            });
          }

          return {
            ...msg,
            content: nextContent,
            reasoning: nextReasoning || undefined,
            segments,
            isStreaming: true,
          };
        };

        // 更新 messages
        setMessages((prev) =>
          prev.map((msg) => (msg.id === targetId ? patchMessage(msg) : msg))
        );

        // 同步更新 timeline，否则 ChatContent 看不到流式增量
        setTimeline((prev) =>
          prev.map((item) => {
            if (item.type !== "message") return item;
            if (item.id !== targetId) return item;
            return {
              ...item,
              message: patchMessage(item.message),
            };
          })
        );
      };

      try {
        // 创建控制器并保存引用
        const controller: StreamChatController = { abort: () => {} };
        streamControllerRef.current = controller;

        for await (const event of streamChat({
          user_id: userId,
          conversation_id: convId,
          message: content.trim(),
        }, controller)) {
          console.log('[SSE Event]', event.type, JSON.stringify(event.payload), event);
          const applyAssistantUpdate = (updater: (msg: ChatMessage) => ChatMessage) => {
            // 同上：捕获当前 id，避免 updater 延迟执行时读到被改写后的 assistantMessageId
            const targetId = assistantMessageId;
            setMessages((prev) =>
              prev.map((msg) => (msg.id === targetId ? updater(msg) : msg))
            );
          };

          if (event.type === "meta.start") {
            const payload = event.payload as Extract<ChatEvent["payload"], { assistant_message_id: string }>;
            // 捕获 clientId，避免 setMessages 延迟执行导致用到被改写后的 assistantMessageId
            const clientId = assistantMessageId;
            if (payload?.assistant_message_id && payload.assistant_message_id !== clientId) {
              const serverId = payload.assistant_message_id;
              // 将前端临时 id 替换为服务端 message_id，保证渲染与落库对齐
              setMessages((prev) =>
                prev.map((msg) => (msg.id === clientId ? { ...msg, id: serverId } : msg))
              );
              // 同步更新 timeline 中的 message id
              setTimeline((prev) =>
                prev.map((item) =>
                  item.type === "message" && item.id === clientId
                    ? { ...item, id: serverId, message: { ...item.message, id: serverId } }
                    : item
                )
              );
              assistantMessageId = serverId;
              console.log("[chat] assistant_message_id remap", { clientId, serverId });
            }
            continue;
          }
          
          // 处理 LLM 调用开始事件：更新 message.llm + message.trace，插入空 reasoning segment
          if (event.type === "llm.call.start") {
            const payload = event.payload as LlmCallStartPayload;
            const llmCallId = crypto.randomUUID();
            const now = Date.now();
            const targetId = assistantMessageId;
            
            // 更新 message.llm 和 trace，同时插入空 reasoning segment 确保推理标题立刻出现
            const patchLlmStart = (msg: ChatMessage): ChatMessage => {
              const trace = [...(msg.trace || [])];
              trace.push({
                id: llmCallId,
                kind: "llm" as const,
                status: "running" as const,
                startedAt: now,
                messageCount: payload?.message_count,
              });
              
              // 如果没有 reasoning segment，插入一个空的确保推理标题出现
              const segments = [...(msg.segments || [])];
              const hasReasoning = segments.some(s => s.kind === "reasoning");
              if (!hasReasoning) {
                segments.push({
                  id: crypto.randomUUID(),
                  kind: "reasoning" as const,
                  text: "",
                  isOpen: true,
                });
              }
              
              return {
                ...msg,
                llm: { status: "running" as const, messageCount: payload?.message_count },
                trace,
                segments,
                isStreaming: true,
              };
            };
            
            setMessages((prev) => prev.map((msg) => msg.id === targetId ? patchLlmStart(msg) : msg));
            setTimeline((prev) => prev.map((item) => 
              item.id === targetId ? { ...item, message: patchLlmStart(item.message) } : item
            ));
            console.log("[chat] llm.call.start", { llmCallId, messageCount: payload?.message_count });
            continue;
          }
          
          // 处理 LLM 调用结束事件：更新 message.llm 状态和 trace
          if (event.type === "llm.call.end") {
            const payload = event.payload as LlmCallEndPayload;
            const hasError = !!payload?.error;
            const now = Date.now();
            const targetId = assistantMessageId;
            
            const patchLlmEnd = (msg: ChatMessage): ChatMessage => {
              // 更新 trace 中最后一个 running 的 llm step
              const trace = [...(msg.trace || [])];
              for (let i = trace.length - 1; i >= 0; i--) {
                const step = trace[i];
                if (step.kind === "llm" && step.status === "running") {
                  trace[i] = {
                    ...step,
                    status: hasError ? "error" as const : "success" as const,
                    endedAt: now,
                    elapsedMs: payload?.elapsed_ms ?? (now - step.startedAt),
                    error: payload?.error,
                  };
                  break;
                }
              }
              
              return {
                ...msg,
                llm: {
                  status: hasError ? "error" as const : "success" as const,
                  elapsedMs: payload?.elapsed_ms,
                  error: payload?.error,
                  messageCount: msg.llm?.messageCount,
                },
                trace,
              };
            };
            
            setMessages((prev) => prev.map((msg) => msg.id === targetId ? patchLlmEnd(msg) : msg));
            setTimeline((prev) => prev.map((item) =>
              item.id === targetId ? { ...item, message: patchLlmEnd(item.message) } : item
            ));
            console.log("[chat] llm.call.end", { hasError, elapsedMs: payload?.elapsed_ms });
            continue;
          }
          
          // 处理工具开始事件：更新 message.toolsSummary + message.trace
          if (event.type === "tool.start") {
            const payload = event.payload as ToolStartPayload;
            const toolName = payload?.name || "unknown";
            const toolCallId = crypto.randomUUID();
            const toolLabel = getToolLabel(toolName);
            const now = Date.now();
            const targetId = assistantMessageId;
            
            // 记录到按 messageId 隔离的调用栈
            const msgStack = inFlightToolStackRef.current[targetId] || {};
            if (!msgStack[toolName]) {
              msgStack[toolName] = [];
            }
            msgStack[toolName].push(toolCallId);
            inFlightToolStackRef.current[targetId] = msgStack;
            
            const patchToolStart = (msg: ChatMessage): ChatMessage => {
              const trace = [...(msg.trace || [])];
              trace.push({
                id: toolCallId,
                kind: "tool" as const,
                name: toolName,
                label: toolLabel,
                status: "running" as const,
                startedAt: now,
              });
              
              const toolsSummary = { ...(msg.toolsSummary || { runningCount: 0 }) };
              toolsSummary.runningCount = (toolsSummary.runningCount || 0) + 1;
              toolsSummary.last = { name: toolName, label: toolLabel, status: "running" as const };
              
              return { ...msg, trace, toolsSummary };
            };
            
            setMessages((prev) => prev.map((msg) => msg.id === targetId ? patchToolStart(msg) : msg));
            setTimeline((prev) => prev.map((item) =>
              item.id === targetId ? { ...item, message: patchToolStart(item.message) } : item
            ));
            console.log("[chat] tool.start", { toolName, toolLabel, toolCallId });
            continue;
          }
          
          // 处理工具结束事件：更新 message.toolsSummary + message.trace
          if (event.type === "tool.end") {
            const payload = event.payload as ToolEndPayload;
            const toolName = payload?.name || "unknown";
            const toolLabel = getToolLabel(toolName);
            const hasError = !!payload?.error;
            const now = Date.now();
            const targetId = assistantMessageId;
            
            // 从按 messageId 隔离的调用栈取出 toolCallId（LIFO）
            const msgStack = inFlightToolStackRef.current[targetId] || {};
            const stack = msgStack[toolName] || [];
            const toolCallId = stack.pop();
            
            const patchToolEnd = (msg: ChatMessage): ChatMessage => {
              const trace = [...(msg.trace || [])];
              
              if (toolCallId) {
                // 找到 trace 中对应的 tool step 并更新
                for (let i = trace.length - 1; i >= 0; i--) {
                  const step = trace[i];
                  if (step.kind === "tool" && step.id === toolCallId) {
                    const elapsedMs = now - step.startedAt;
                    trace[i] = {
                      ...step,
                      status: hasError ? "error" as const : "success" as const,
                      endedAt: now,
                      elapsedMs,
                      count: payload?.count,
                      error: payload?.error,
                    };
                    break;
                  }
                }
              } else {
                // 没有匹配的 start，补一条完成的 step
                trace.push({
                  id: crypto.randomUUID(),
                  kind: "tool" as const,
                  name: toolName,
                  label: toolLabel,
                  status: hasError ? "error" as const : "success" as const,
                  startedAt: now,
                  endedAt: now,
                  elapsedMs: 0,
                  count: payload?.count,
                  error: payload?.error,
                });
              }
              
              const toolsSummary = { ...(msg.toolsSummary || { runningCount: 0 }) };
              toolsSummary.runningCount = Math.max(0, (toolsSummary.runningCount || 0) - 1);
              
              // 找到刚才更新的 step 获取 elapsedMs
              const updatedStep = trace.find(s => s.kind === "tool" && s.id === toolCallId);
              toolsSummary.last = {
                name: toolName,
                label: toolLabel,
                status: hasError ? "error" as const : "success" as const,
                elapsedMs: updatedStep && updatedStep.kind === "tool" ? updatedStep.elapsedMs : 0,
                count: payload?.count,
                error: payload?.error,
              };
              
              return { ...msg, trace, toolsSummary };
            };
            
            setMessages((prev) => prev.map((msg) => msg.id === targetId ? patchToolEnd(msg) : msg));
            setTimeline((prev) => prev.map((item) =>
              item.id === targetId ? { ...item, message: patchToolEnd(item.message) } : item
            ));
            console.log("[chat] tool.end", { toolName, toolCallId, hasError, count: payload?.count });
            continue;
          }
          
          if (event.type === "assistant.delta") {
            const payload = event.payload as Extract<ChatEvent["payload"], { delta: string }>;
            if (payload?.delta) {
              // 不合帧：后端返回多长增量，就立刻显示多长
              fullContent += payload.delta;
              applyAssistantSegmentsDelta("content", payload.delta, fullContent, fullReasoning);
            }
          } else if (event.type === "assistant.reasoning.delta") {
            const payload = event.payload as Extract<ChatEvent["payload"], { delta: string }>;
            if (payload?.delta) {
              // 不合帧：后端返回多长增量，就立刻显示多长
              fullReasoning += payload.delta;
              applyAssistantSegmentsDelta("reasoning", payload.delta, fullContent, fullReasoning);
            }
          } else if (event.type === "assistant.products") {
            const payload = event.payload as Extract<ChatEvent["payload"], { items: Product[] }>;
            if (payload?.items) {
              products = payload.items;
              const targetId = assistantMessageId;
              const now = Date.now();
              
              // 更新 products 并添加 trace 记录
              const patchProducts = (msg: ChatMessage): ChatMessage => {
                const trace = [...(msg.trace || [])];
                trace.push({
                  id: crypto.randomUUID(),
                  kind: "products" as const,
                  count: payload.items.length,
                  ts: now,
                });
                return { ...msg, products, trace };
              };
              
              setMessages((prev) => prev.map((msg) => msg.id === targetId ? patchProducts(msg) : msg));
              setTimeline((prev) => prev.map((item) =>
                item.id === targetId ? { ...item, message: patchProducts(item.message) } : item
              ));
            }
          } else if (event.type === "assistant.final") {
            const payload = event.payload as Extract<ChatEvent["payload"], { content: string; reasoning?: string | null; products?: Product[] | null }>;
            if (typeof payload?.content === "string" && payload.content) {
              // final 以服务端为准：如果更长/不同，补齐差异（避免覆盖导致丢段）
              if (payload.content.startsWith(fullContent)) {
                const rest = payload.content.slice(fullContent.length);
                if (rest) {
                  fullContent = payload.content;
                  applyAssistantSegmentsDelta("content", rest, fullContent, fullReasoning);
                } else {
                  fullContent = payload.content;
                }
              } else if (payload.content.length >= fullContent.length) {
                fullContent = payload.content;
              }
            }
            if (typeof payload?.reasoning === "string" && payload.reasoning) {
              if (payload.reasoning.startsWith(fullReasoning)) {
                const rest = payload.reasoning.slice(fullReasoning.length);
                if (rest) {
                  fullReasoning = payload.reasoning;
                  applyAssistantSegmentsDelta("reasoning", rest, fullContent, fullReasoning);
                } else {
                  fullReasoning = payload.reasoning;
                }
              } else if (payload.reasoning.length >= fullReasoning.length) {
                fullReasoning = payload.reasoning;
              }
            }
            if (payload?.products && Array.isArray(payload.products)) {
              products = payload.products;
            }

            applyAssistantUpdate((msg) => ({ ...msg, content: fullContent, reasoning: fullReasoning || undefined, products, isStreaming: false }));
            
            // 同步更新 timeline 中的 assistant message
            const targetId = assistantMessageId;
            setTimeline((prev) =>
              prev.map((item) =>
                item.type === "message" && item.id === targetId
                  ? {
                      ...item,
                      message: {
                        ...item.message,
                        content: fullContent,
                        reasoning: fullReasoning || undefined,
                        products,
                        isStreaming: false,
                      },
                    }
                  : item
              )
            );
            
            // 更新会话标题（使用用户第一条消息）
            if (messages.length === 0 && onTitleUpdate) {
              const title = content.slice(0, 50) + (content.length > 50 ? "..." : "");
              onTitleUpdate(title);
            }
          } else if (event.type === "error") {
            const payload = event.payload as Extract<ChatEvent["payload"], { message: string }>;
            throw new Error(payload?.message || "聊天出错");
          }
        }
      } catch (error) {
        // 如果不是用户主动中断，才显示错误
        if (error instanceof Error && error.name !== 'AbortError') {
          setError(error.message);
          const targetId = assistantMessageId;
          setMessages((prev) => prev.filter((msg) => msg.id !== targetId));
          // 同步清理 timeline：移除出错的 assistant 消息
          setTimeline((prev) => prev.filter((item) => item.id !== targetId));
        }
      } finally {
        inFlightToolStackRef.current = {};
        streamControllerRef.current = null;
        setIsSending(false); // 发送完成
        setIsStreaming(false);
      }
    },
    [userId, conversationId, messages.length, onTitleUpdate]
  );

  // 清空消息
  const clearMessages = useCallback(() => {
    setMessages([]);
    setTimeline([]);
    setError(null);
  }, []);

  // 当会话 ID 变化时重新加载消息
  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  return {
    messages,
    timeline,
    isLoading,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
    refreshMessages: loadMessages,
    abortStream,
  };
}
