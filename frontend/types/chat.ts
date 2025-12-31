// 聊天相关类型

import type { Product } from "@/types/product";

/**
 * ## Chat SSE 协议（前端消费说明）
 *
 * 后端通过 SSE（`text/event-stream`）逐条推送 JSON，每条 SSE frame 形如：
 *
 * - `data: { ...StreamEvent... }\n\n`
 *
 * 你在 `streamChat()` 里会把 `data:` 后面的 JSON parse 成 `ChatEvent`，然后在 `useChat` 里
 * 根据 `event.type` 做渲染更新（推荐用 switch/handler map 的 reducer 方式）。
 *
 * ### 统一 Envelope 字段（所有事件都有）
 * - `v`: 协议版本（目前固定 1）
 * - `id`: 事件唯一 ID（用于排查/追踪）
 * - `seq`: 单条流内递增序号（用于排序/去重）
 * - `ts`: 毫秒时间戳
 * - `conversation_id`: 会话 ID
 * - `message_id`: 助手消息 ID（关键：用于前端渲染与后端落库对齐）
 * - `type`: 事件类型（见下方枚举）
 * - `payload`: 事件数据（由 type 决定结构）
 *
 * ### 事件类型与 payload 结构（重点）
 *
 * - `meta.start`：
 *   - payload: `{ user_message_id: string; assistant_message_id: string }`
 *   - 用途：开流第一条事件，告诉前端本次助手消息的服务端 `assistant_message_id`。
 *     前端应当把本地临时 assistant message 的 id 替换成它（保证刷新/落库一致）。
 *
 * - `assistant.delta`：
 *   - payload: `{ delta: string }`
 *   - 用途：模型生成的文本增量。前端应当把 delta 追加到当前 assistant message 的 content。
 *
 * - `assistant.reasoning.delta`（可选）：
 *   - payload: `{ delta: string }`
 *   - 用途：推理增量（如果模型支持）。是否展示由你决定（可用于 Debug 面板）。
 *
 * - `assistant.products`：
 *   - payload: `{ items: Product[] }`
 *   - 用途：工具检索/解析出的商品列表。前端可在 assistant message 下渲染商品卡片。
 *
 * - `assistant.final`：
 *   - payload: `{ content: string; reasoning?: string | null; products?: Product[] | null }`
 *   - 用途：最终态（流结束前必出）。前端可用它纠正最终 content/products，并把 isStreaming=false。
 *
 * - `tool.start` / `tool.end`（可选）：
 *   - payload 示例：
 *     - tool.start: `{ name: string; input?: unknown }`
 *     - tool.end: `{ name: string; count?: number; output_preview?: unknown; error?: string }`
 *   - 用途：展示“正在检索/已完成”等过程提示，或用于 Debug。
 *
 * - `llm.call.start` / `llm.call.end`（可选）：
 *   - payload 示例：
 *     - llm.call.start: `{ message_count: number }`
 *     - llm.call.end: `{ elapsed_ms: number; message_count?: number; error?: string }`
 *   - 用途：展示“思考中/生成中”的状态，或用于 Debug/性能监控。
 *
 * - `error`：
 *   - payload: `{ message: string; code?: string; detail?: unknown }`
 *   - 用途：后端异常或中断。前端应当终止本次流并展示错误。
 *
 * ### 前端使用示例（伪代码）
 *
 * ```ts
 * for await (const event of streamChat(req)) {
 *   switch (event.type) {
 *     case "meta.start": {
 *       const { assistant_message_id } = event.payload
 *       // 替换本地临时 id -> assistant_message_id
 *       break
 *     }
 *     case "assistant.delta": {
 *       state.content += event.payload.delta
 *       break
 *     }
 *     case "assistant.products": {
 *       state.products = event.payload.items
 *       break
 *     }
 *     case "assistant.final": {
 *       state.content = event.payload.content
 *       state.products = event.payload.products ?? state.products
 *       state.isStreaming = false
 *       break
 *     }
 *     case "error": throw new Error(event.payload.message)
 *   }
 * }
 * ```
 */
export interface ChatRequest {
  user_id: string;
  conversation_id: string;
  message: string;
}

/**
 * LLM 调用内部事件（在 llm.call.start → llm.call.end 之间触发）
 * 对应后端 LLMCallDomainEventType
 */
export type LLMCallInternalEventType =
  | "assistant.reasoning.delta"
  | "assistant.delta"
  | "assistant.products"
  | "tool.start"
  | "tool.end"
  | "context.summarized"
  | "assistant.todos";

/**
 * 非 LLM 调用内部事件（与 LLM 调用并列或跨调用）
 * 对应后端 NonLLMCallDomainEventType
 */
export type NonLLMCallEventType =
  | "meta.start"
  | "assistant.final"
  | "llm.call.start"
  | "llm.call.end"
  | "memory.extraction.start"
  | "memory.extraction.complete"
  | "memory.profile.updated"
  | "support.handoff_started"
  | "support.handoff_ended"
  | "support.human_message"
  | "support.connected"
  | "support.ping"
  | "error";

/** 所有事件类型 */
export type ChatEventType = LLMCallInternalEventType | NonLLMCallEventType;

/** 判断是否为 LLM 调用内部事件 */
export function isLLMCallInternalEvent(type: string): type is LLMCallInternalEventType {
  return [
    "assistant.reasoning.delta",
    "assistant.delta",
    "assistant.products",
    "tool.start",
    "tool.end",
    "context.summarized",
    "assistant.todos",
  ].includes(type);
}

export interface MetaStartPayload {
  user_message_id: string;
  assistant_message_id: string;
}

export interface TextDeltaPayload {
  delta: string;
}

export interface ProductsPayload {
  items: Product[];
}

export interface TodoItem {
  content: string;
  status: "pending" | "in_progress" | "completed";
}

export interface TodosPayload {
  todos: TodoItem[];
}

export interface FinalPayload {
  content: string;
  reasoning?: string | null;
  products?: Product[] | null;
}

export interface ToolStartPayload {
  tool_call_id: string;
  name: string;
  input?: unknown;
}

export interface ToolEndPayload {
  tool_call_id: string;
  name: string;
  status?: "success" | "error" | "empty";
  count?: number;
  output_preview?: unknown;
  error?: string;
}

export interface LlmCallStartPayload {
  message_count: number;
  llm_call_id?: string;
}

export interface LlmCallEndPayload {
  elapsed_ms: number;
  message_count?: number;
  error?: string;
  llm_call_id?: string;
}

export interface ErrorPayload {
  message: string;
  code?: string;
  detail?: unknown;
}

export interface ContextSummarizedPayload {
  messages_before: number;
  messages_after: number;
  tokens_before?: number;
  tokens_after?: number;
}

export interface MemoryExtractionPayload {
  extraction_id?: string;
  status?: string;
}

export interface MemoryProfilePayload {
  profile_id?: string;
  updated_fields?: string[];
}

export interface SupportEventPayload {
  session_id?: string;
  agent_id?: string;
  message?: string;
}

export type ChatEventPayload =
  | MetaStartPayload
  | TextDeltaPayload
  | ProductsPayload
  | TodosPayload
  | FinalPayload
  | ToolStartPayload
  | ToolEndPayload
  | LlmCallStartPayload
  | LlmCallEndPayload
  | ErrorPayload
  | ContextSummarizedPayload
  | MemoryExtractionPayload
  | MemoryProfilePayload
  | SupportEventPayload
  | Record<string, unknown>;

export interface ChatEventBase {
  v: number;
  id: string;
  seq: number;
  ts: number;
  conversation_id: string;
  message_id?: string | null;
}

export type ChatEvent =
  // ========== 非 LLM 调用内部事件 ==========
  | (ChatEventBase & { type: "meta.start"; payload: MetaStartPayload })
  | (ChatEventBase & { type: "assistant.final"; payload: FinalPayload })
  | (ChatEventBase & { type: "llm.call.start"; payload: LlmCallStartPayload })
  | (ChatEventBase & { type: "llm.call.end"; payload: LlmCallEndPayload })
  | (ChatEventBase & { type: "memory.extraction.start"; payload: MemoryExtractionPayload })
  | (ChatEventBase & { type: "memory.extraction.complete"; payload: MemoryExtractionPayload })
  | (ChatEventBase & { type: "memory.profile.updated"; payload: MemoryProfilePayload })
  | (ChatEventBase & { type: "support.handoff_started"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "support.handoff_ended"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "support.human_message"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "support.connected"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "support.ping"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "error"; payload: ErrorPayload })
  // ========== LLM 调用内部事件 ==========
  | (ChatEventBase & { type: "assistant.reasoning.delta"; payload: TextDeltaPayload })
  | (ChatEventBase & { type: "assistant.delta"; payload: TextDeltaPayload })
  | (ChatEventBase & { type: "assistant.products"; payload: ProductsPayload })
  | (ChatEventBase & { type: "tool.start"; payload: ToolStartPayload })
  | (ChatEventBase & { type: "tool.end"; payload: ToolEndPayload })
  | (ChatEventBase & { type: "context.summarized"; payload: ContextSummarizedPayload })
  | (ChatEventBase & { type: "assistant.todos"; payload: TodosPayload })
  // ========== 兜底 ==========
  | (ChatEventBase & { type: ChatEventType; payload: Record<string, unknown> });
