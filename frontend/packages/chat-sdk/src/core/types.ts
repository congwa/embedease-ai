/**
 * Chat SDK 核心类型定义
 *
 * 从 frontend/types/chat.ts 抽离
 */

// ==================== 图片附件 ====================

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

// ==================== 请求类型 ====================

export interface ChatRequest {
  user_id: string;
  conversation_id: string;
  message: string;
  images?: ImageAttachment[];
}

// ==================== 事件类型分类 ====================

/** 流级别事件：贯穿整个 SSE 流的生命周期 */
export type StreamLevelEventType = "meta.start" | "assistant.final" | "error";

/** LLM 调用边界事件：标记单次 LLM 调用的开始和结束 */
export type LLMCallBoundaryEventType = "llm.call.start" | "llm.call.end";

/** LLM 调用内部事件：仅在 llm.call.start → llm.call.end 之间触发 */
export type LLMCallInternalEventType =
  | "assistant.reasoning.delta"
  | "assistant.delta";

/** 工具调用事件 */
export type ToolCallEventType = "tool.start" | "tool.end";

/** 数据事件 */
export type DataEventType =
  | "assistant.products"
  | "assistant.todos"
  | "context.summarized";

/** 后处理事件 */
export type PostProcessEventType =
  | "memory.extraction.start"
  | "memory.extraction.complete"
  | "memory.profile.updated";

/** 客服支持事件 */
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

/** Supervisor 多 Agent 编排事件 */
export type SupervisorEventType =
  | "agent.routed"
  | "agent.handoff"
  | "agent.complete";

/** 技能事件 */
export type SkillEventType = "skill.activated" | "skill.loaded";

/** 中间件事件 */
export type MiddlewareEventType =
  | "model.retry.start"
  | "model.retry.failed"
  | "model.fallback"
  | "model.call_limit.exceeded"
  | "context.edited";

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
  | MiddlewareEventType
  | SkillEventType;

// ==================== 事件类型判断函数 ====================

export function isLLMCallInternalEvent(
  type: string
): type is LLMCallInternalEventType {
  return ["assistant.reasoning.delta", "assistant.delta"].includes(type);
}

export function isToolCallEvent(type: string): type is ToolCallEventType {
  return ["tool.start", "tool.end"].includes(type);
}

export function isDataEvent(type: string): type is DataEventType {
  return ["assistant.products", "assistant.todos", "context.summarized"].includes(
    type
  );
}

// ==================== 事件基础结构 ====================

export interface ChatEventBase {
  /** 协议版本 */
  v: number;
  /** 事件唯一 ID */
  id: string;
  /** 序号（递增） */
  seq: number;
  /** 毫秒时间戳 */
  ts: number;
  /** 会话 ID */
  conversation_id: string;
  /** 消息 ID */
  message_id?: string | null;
}
