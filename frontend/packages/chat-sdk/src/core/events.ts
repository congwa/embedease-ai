/**
 * Chat SDK 事件类型定义
 */

import type { ChatEventBase, ChatEventType } from "./types";
import type {
  MetaStartPayload,
  TextDeltaPayload,
  ProductsPayload,
  TodosPayload,
  FinalPayload,
  ToolStartPayload,
  ToolEndPayload,
  LlmCallStartPayload,
  LlmCallEndPayload,
  ErrorPayload,
  ContextSummarizedPayload,
  MemoryExtractionPayload,
  MemoryProfilePayload,
  SupportEventPayload,
  AgentRoutedPayload,
  AgentHandoffPayload,
  AgentCompletePayload,
  SkillActivatedPayload,
  SkillLoadedPayload,
  ModelRetryStartPayload,
  ModelRetryFailedPayload,
  ModelFallbackPayload,
  ModelCallLimitExceededPayload,
  ContextEditedPayload,
} from "./payloads";

/**
 * 完整事件类型（联合类型，类型安全）
 */
export type ChatEvent =
  // ========== 流级别事件 ==========
  | (ChatEventBase & { type: "meta.start"; payload: MetaStartPayload })
  | (ChatEventBase & { type: "assistant.final"; payload: FinalPayload })
  | (ChatEventBase & { type: "error"; payload: ErrorPayload })
  // ========== LLM 调用边界事件 ==========
  | (ChatEventBase & { type: "llm.call.start"; payload: LlmCallStartPayload })
  | (ChatEventBase & { type: "llm.call.end"; payload: LlmCallEndPayload })
  // ========== LLM 调用内部事件 ==========
  | (ChatEventBase & {
      type: "assistant.reasoning.delta";
      payload: TextDeltaPayload;
    })
  | (ChatEventBase & { type: "assistant.delta"; payload: TextDeltaPayload })
  // ========== 工具调用事件 ==========
  | (ChatEventBase & { type: "tool.start"; payload: ToolStartPayload })
  | (ChatEventBase & { type: "tool.end"; payload: ToolEndPayload })
  // ========== 数据事件 ==========
  | (ChatEventBase & { type: "assistant.products"; payload: ProductsPayload })
  | (ChatEventBase & { type: "assistant.todos"; payload: TodosPayload })
  | (ChatEventBase & {
      type: "context.summarized";
      payload: ContextSummarizedPayload;
    })
  // ========== 后处理事件 ==========
  | (ChatEventBase & {
      type: "memory.extraction.start";
      payload: MemoryExtractionPayload;
    })
  | (ChatEventBase & {
      type: "memory.extraction.complete";
      payload: MemoryExtractionPayload;
    })
  | (ChatEventBase & {
      type: "memory.profile.updated";
      payload: MemoryProfilePayload;
    })
  // ========== 客服支持事件 ==========
  | (ChatEventBase & {
      type: "support.handoff_started";
      payload: SupportEventPayload;
    })
  | (ChatEventBase & {
      type: "support.handoff_ended";
      payload: SupportEventPayload;
    })
  | (ChatEventBase & {
      type: "support.human_message";
      payload: SupportEventPayload;
    })
  | (ChatEventBase & { type: "support.human_mode"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "support.connected"; payload: SupportEventPayload })
  | (ChatEventBase & { type: "support.ping"; payload: SupportEventPayload })
  // ========== Supervisor 事件 ==========
  | (ChatEventBase & { type: "agent.routed"; payload: AgentRoutedPayload })
  | (ChatEventBase & { type: "agent.handoff"; payload: AgentHandoffPayload })
  | (ChatEventBase & { type: "agent.complete"; payload: AgentCompletePayload })
  // ========== 技能事件 ==========
  | (ChatEventBase & { type: "skill.activated"; payload: SkillActivatedPayload })
  | (ChatEventBase & { type: "skill.loaded"; payload: SkillLoadedPayload })
  // ========== 中间件事件 ==========
  | (ChatEventBase & {
      type: "model.retry.start";
      payload: ModelRetryStartPayload;
    })
  | (ChatEventBase & {
      type: "model.retry.failed";
      payload: ModelRetryFailedPayload;
    })
  | (ChatEventBase & { type: "model.fallback"; payload: ModelFallbackPayload })
  | (ChatEventBase & {
      type: "model.call_limit.exceeded";
      payload: ModelCallLimitExceededPayload;
    })
  | (ChatEventBase & { type: "context.edited"; payload: ContextEditedPayload })
  // ========== 兜底 ==========
  | (ChatEventBase & { type: ChatEventType; payload: Record<string, unknown> });
