/**
 * Zustand Stores 统一导出
 */

export { useUserStore } from "./user-store";
export { useConversationStore } from "./conversation-store";
export { useChatStore } from "./chat-store";
export { useAgentStore, type Agent } from "./agent-store";
export { useRealtimeStore, type RealtimeState } from "./realtime-store";
export { useSupportStore, type SupportState } from "./support-store";
export {
  useSupportWorkbenchStore,
  type SupportWorkbenchState,
  type ConversationWithPreview,
  type UserConversationGroup,
} from "./support-workbench-store";
export {
  useSystemStore,
  type SystemFeatures,
  type FeatureStatus,
  type MemoryFeature,
} from "./system-store";
export {
  useModeStore,
  useIsSupervisorMode,
  useModeDisplayName,
  type SystemMode,
  type SupervisorConfig,
  type SubAgentConfig,
} from "./mode-store";

// 重新导出 timeline 类型供组件使用
export type {
  TimelineState,
  TimelineItem,
  UserMessageItem,
  LLMCallClusterItem,
  ToolCallItem,
  ErrorItem,
  FinalItem,
  MemoryEventItem,
  SupportEventItem,
  GreetingItem,
  LLMCallSubItem,
  ReasoningSubItem,
  ContentSubItem,
  ProductsSubItem,
  TodosSubItem,
  ContextSummarizedSubItem,
} from "@/lib/timeline-utils";
