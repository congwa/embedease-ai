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
export interface ImageAttachment {
  id: string;
  url: string;
  thumbnail_url?: string;
  filename?: string;
  size?: number;
  width?: number;
  height?: number;
  mime_type?: string;
}

export interface ChatRequest {
  user_id: string;
  conversation_id: string;
  message: string;
  images?: ImageAttachment[];
}

// ==================== 事件类型分类 ====================

/**
 * 流级别事件：贯穿整个 SSE 流的生命周期
 */
export type StreamLevelEventType = "meta.start" | "assistant.final" | "error";

/**
 * LLM 调用边界事件：标记单次 LLM 调用的开始和结束
 */
export type LLMCallBoundaryEventType = "llm.call.start" | "llm.call.end";

/**
 * LLM 调用内部事件：仅在 llm.call.start → llm.call.end 之间触发
 */
export type LLMCallInternalEventType = "assistant.reasoning.delta" | "assistant.delta";

/**
 * 工具调用事件：在 llm.call.end 之后触发，独立于 LLM 调用
 * 
 * 真实事件流：
 * llm.call.start → [reasoning.delta, delta...] → llm.call.end
 * → tool.start → [中间推送] → tool.end
 * → llm.call.start → [...] → llm.call.end (下一轮)
 */
export type ToolCallEventType = "tool.start" | "tool.end";

/**
 * 数据事件：可能在 LLM 调用内部或工具执行时产生
 */
export type DataEventType = "assistant.products" | "assistant.todos" | "context.summarized";

/**
 * 后处理事件：流末尾的后处理操作
 */
export type PostProcessEventType =
  | "memory.extraction.start"
  | "memory.extraction.complete"
  | "memory.profile.updated";

/**
 * 客服支持事件
 */
export type SupportEventType =
  | "support.handoff_started"
  | "support.handoff_ended"
  | "support.human_message"
  | "support.human_mode"
  | "support.connected"
  | "support.ping"
  | "support.message_withdrawn"
  | "support.message_edited"
  | "support.messages_deleted";

/**
 * Supervisor 多 Agent 编排事件
 */
export type SupervisorEventType =
  | "agent.routed"
  | "agent.handoff"
  | "agent.complete";

/**
 * 技能事件
 */
export type SkillEventType = "skill.activated" | "skill.loaded";

/** 所有事件类型 */
export type ChatEventType =
  | StreamLevelEventType
  | LLMCallBoundaryEventType
  | LLMCallInternalEventType
  | ToolCallEventType
  | DataEventType
  | PostProcessEventType
  | SupportEventType
  | SupervisorEventType
  | SkillEventType;

// ==================== 事件类型判断函数 ====================

/** 判断是否为 LLM 调用内部事件（仅 reasoning.delta 和 delta） */
export function isLLMCallInternalEvent(type: string): type is LLMCallInternalEventType {
  return ["assistant.reasoning.delta", "assistant.delta"].includes(type);
}

/** 判断是否为工具调用事件 */
export function isToolCallEvent(type: string): type is ToolCallEventType {
  return ["tool.start", "tool.end"].includes(type);
}

/** 判断是否为数据事件 */
export function isDataEvent(type: string): type is DataEventType {
  return ["assistant.products", "assistant.todos", "context.summarized"].includes(type);
}

// ==================== 兼容旧代码的类型别名 ====================

/** @deprecated 使用更细粒度的事件类型 */
export type NonLLMCallEventType =
  | StreamLevelEventType
  | LLMCallBoundaryEventType
  | PostProcessEventType
  | SupportEventType;

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
  content?: string;      // 客服消息内容
  operator?: string;     // 客服 ID
  message_id?: string;   // 消息 ID
  created_at?: string;   // 创建时间
}

// ========== Supervisor 事件 Payload ==========

export interface AgentRoutedPayload {
  source_agent: string;
  target_agent: string;
  target_agent_name: string;
  reason?: string;
}

export interface AgentHandoffPayload {
  from_agent: string;
  to_agent: string;
  to_agent_name: string;
  task?: string;
}

export interface AgentCompletePayload {
  agent_id: string;
  agent_name: string;
  elapsed_ms?: number;
  status?: string;
}

// ========== 技能事件 Payload ==========

export interface SkillActivatedPayload {
  skill_id: string;
  skill_name: string;
  trigger_type: "keyword" | "intent" | "manual";
  trigger_keyword?: string;
}

export interface SkillLoadedPayload {
  skill_id: string;
  skill_name: string;
  skill_category: string;
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
  | AgentRoutedPayload
  | AgentHandoffPayload
  | AgentCompletePayload
  | SkillActivatedPayload
  | SkillLoadedPayload
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
  | (ChatEventBase & { type: "support.human_mode"; payload: SupportEventPayload })
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
  // ========== Supervisor 事件 ==========
  | (ChatEventBase & { type: "agent.routed"; payload: AgentRoutedPayload })
  | (ChatEventBase & { type: "agent.handoff"; payload: AgentHandoffPayload })
  | (ChatEventBase & { type: "agent.complete"; payload: AgentCompletePayload })
  // ========== 技能事件 ==========
  | (ChatEventBase & { type: "skill.activated"; payload: SkillActivatedPayload })
  | (ChatEventBase & { type: "skill.loaded"; payload: SkillLoadedPayload })
  // ========== 兜底 ==========
  | (ChatEventBase & { type: ChatEventType; payload: Record<string, unknown> });
