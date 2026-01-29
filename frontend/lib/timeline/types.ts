/**
 * Timeline 类型定义
 */

import type { Product } from "@/types/product";
import type { TodoItem, ImageAttachment } from "@/types/chat";

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

export type ToolCallSubItem = ProductsSubItem | TodosSubItem | ContextSummarizedSubItem;

// ==================== 时间线顶层 Item 类型 ====================

export interface UserMessageItem {
  type: "user.message";
  id: string;
  turnId: string;
  content: string;
  images?: ImageAttachment[];
  ts: number;
  // 撤回/编辑相关
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
  eventType: "handoff_started" | "handoff_ended" | "human_message" | "connected" | "human_mode";
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

// ==================== 兼容旧组件的类型别名 ====================

export interface ReasoningItem {
  type: "assistant.reasoning";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

export interface ContentItem {
  type: "assistant.content";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  ts: number;
}

export interface ProductsItem {
  type: "assistant.products";
  id: string;
  turnId: string;
  products: Product[];
  ts: number;
}

export interface TodosItem {
  type: "assistant.todos";
  id: string;
  turnId: string;
  todos: TodoItem[];
  ts: number;
}

export interface ContextSummarizedItem {
  type: "context.summarized";
  id: string;
  turnId: string;
  messagesBefore: number;
  messagesAfter: number;
  tokensBefore?: number;
  tokensAfter?: number;
  ts: number;
}
