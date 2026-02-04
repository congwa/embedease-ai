/**
 * Chat SDK Payload 类型定义
 */

// ==================== 产品类型（SDK 内部定义） ====================

export interface Product {
  id: string;
  name: string;
  price?: number;
  image_url?: string;
  url?: string;
  description?: string;
  [key: string]: unknown;
}

// ==================== 基础 Payload ====================

export interface MetaStartPayload {
  user_message_id: string;
  assistant_message_id: string;
  mode?: string;
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

// ==================== 工具调用 Payload ====================

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

// ==================== LLM 调用 Payload ====================

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

// ==================== 错误 Payload ====================

export interface ErrorPayload {
  message: string;
  code?: string;
  detail?: unknown;
}

// ==================== 上下文压缩 Payload ====================

export interface ContextSummarizedPayload {
  messages_before: number;
  messages_after: number;
  tokens_before?: number;
  tokens_after?: number;
}

// ==================== 记忆 Payload ====================

export interface MemoryExtractionPayload {
  extraction_id?: string;
  status?: string;
}

export interface MemoryProfilePayload {
  profile_id?: string;
  updated_fields?: string[];
}

// ==================== 客服支持 Payload ====================

export interface SupportEventPayload {
  session_id?: string;
  agent_id?: string;
  message?: string;
  content?: string;
  operator?: string;
  message_id?: string;
  created_at?: string;
}

// ==================== Supervisor Payload ====================

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

// ==================== 技能 Payload ====================

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

// ==================== 中间件 Payload ====================

export interface ModelRetryStartPayload {
  attempt: number;
  max_retries: number;
  delay_ms: number;
  error_type: string;
  error_message?: string;
}

export interface ModelRetryFailedPayload {
  total_attempts: number;
  final_error: string;
  on_failure: "continue" | "error";
}

export interface ModelFallbackPayload {
  from_model: string;
  to_model: string;
  fallback_index: number;
  total_fallbacks: number;
  error_type: string;
  error_message?: string;
}

export interface ModelCallLimitExceededPayload {
  thread_count?: number;
  run_count?: number;
  thread_limit?: number;
  run_limit?: number;
  exceeded_type: "thread" | "run" | "both";
  exit_behavior: "end" | "error";
}

export interface ContextEditedPayload {
  strategy: string;
  tokens_before?: number;
  tokens_after?: number;
  tools_cleared: number;
  kept: number;
}

// ==================== Payload 联合类型 ====================

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
  | ModelRetryStartPayload
  | ModelRetryFailedPayload
  | ModelFallbackPayload
  | ModelCallLimitExceededPayload
  | ContextEditedPayload
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
