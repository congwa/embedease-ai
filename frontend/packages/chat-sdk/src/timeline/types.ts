/**
 * Timeline 类型定义
 *
 * 从 frontend/lib/timeline/types.ts 抽离
 */

import type { ImageAttachment } from "../core/types";
import type { Product, TodoItem } from "../core/payloads";

/** 状态类型 */
export type ItemStatus = "running" | "success" | "error" | "empty";

// ==================== LLM 调用内部子事件类型 ====================

export interface ReasoningSubItem {
  type: "reasoning";
  id: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

export interface ContentSubItem {
  type: "content";
  id: string;
  text: string;
  ts: number;
}

export interface ProductsSubItem {
  type: "products";
  id: string;
  products: Product[];
  ts: number;
}

export interface TodosSubItem {
  type: "todos";
  id: string;
  todos: TodoItem[];
  ts: number;
}

export interface ContextSummarizedSubItem {
  type: "context_summarized";
  id: string;
  messagesBefore: number;
  messagesAfter: number;
  tokensBefore?: number;
  tokensAfter?: number;
  ts: number;
}

export type LLMCallSubItem =
  | ReasoningSubItem
  | ContentSubItem
  | ProductsSubItem
  | TodosSubItem
  | ContextSummarizedSubItem;

export type ToolCallSubItem =
  | ProductsSubItem
  | TodosSubItem
  | ContextSummarizedSubItem;

// ==================== 时间线顶层 Item 类型 ====================

export interface UserMessageItem {
  type: "user.message";
  id: string;
  turnId: string;
  content: string;
  images?: ImageAttachment[];
  ts: number;
  isWithdrawn?: boolean;
  withdrawnAt?: string;
  withdrawnBy?: string;
  isEdited?: boolean;
  editedAt?: string;
  editedBy?: string;
}

export interface LLMCallClusterItem {
  type: "llm.call.cluster";
  id: string;
  turnId: string;
  status: ItemStatus;
  messageCount?: number;
  elapsedMs?: number;
  error?: string;
  children: LLMCallSubItem[];
  childIndexById: Record<string, number>;
  ts: number;
}

export interface ToolCallItem {
  type: "tool.call";
  id: string;
  turnId: string;
  name: string;
  label: string;
  status: ItemStatus;
  count?: number;
  elapsedMs?: number;
  error?: string;
  input?: unknown;
  children: ToolCallSubItem[];
  childIndexById: Record<string, number>;
  startedAt: number;
  ts: number;
}

export interface ErrorItem {
  type: "error";
  id: string;
  turnId: string;
  message: string;
  ts: number;
}

export interface FinalItem {
  type: "final";
  id: string;
  turnId: string;
  content?: string;
  ts: number;
}

export interface MemoryEventItem {
  type: "memory.event";
  id: string;
  turnId: string;
  eventType: "extraction.start" | "extraction.complete" | "profile.updated";
  ts: number;
}

export interface SupportEventItem {
  type: "support.event";
  id: string;
  turnId: string;
  eventType:
    | "handoff_started"
    | "handoff_ended"
    | "human_message"
    | "connected"
    | "human_mode";
  message?: string;
  content?: string;
  operator?: string;
  messageId?: string;
  ts: number;
}

export interface GreetingItem {
  type: "greeting";
  id: string;
  turnId: string;
  title?: string;
  subtitle?: string;
  body: string;
  cta?: {
    text: string;
    payload: string;
  };
  delayMs: number;
  channel: string;
  ts: number;
}

export interface WaitingItem {
  type: "waiting";
  id: string;
  turnId: string;
  ts: number;
}

export interface SkillActivatedItem {
  type: "skill.activated";
  id: string;
  turnId: string;
  skillId: string;
  skillName: string;
  triggerType: "keyword" | "intent" | "manual";
  triggerKeyword?: string;
  ts: number;
}

export type TimelineItem =
  | UserMessageItem
  | LLMCallClusterItem
  | ToolCallItem
  | ErrorItem
  | FinalItem
  | MemoryEventItem
  | SupportEventItem
  | GreetingItem
  | WaitingItem
  | SkillActivatedItem;

export interface TimelineState {
  timeline: TimelineItem[];
  indexById: Record<string, number>;
  activeTurn: {
    turnId: string | null;
    currentLlmCallId: string | null;
    currentToolCallId: string | null;
    isStreaming: boolean;
  };
}

// ==================== 历史消息类型 ====================

export interface HistoryMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  products?: Product[];
  message_type?: string;
  extra_metadata?: {
    greeting_config?: {
      title?: string;
      subtitle?: string;
      body?: string;
    };
    cta?: { text: string; payload: string };
    delay_ms?: number;
    channel?: string;
  };
}
