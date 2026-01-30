/**
 * Labels 模块统一导出
 * 保持向后兼容，现有代码无需修改 import
 */

// 类型导出
export type {
  ToolCategoryInfo,
  MiddlewareInfo,
  MiddlewarePipelineInfo,
  MiddlewarePipelineInfoExtended,
  ToolInfo,
  PromptLayerInfo,
  PolicyFieldInfo,
} from "./types";

// 工具类别
export { TOOL_CATEGORY_LABELS, getToolCategoryLabel } from "./tool-categories";

// 中间件
export {
  MIDDLEWARE_LABELS,
  getMiddlewareLabel,
  MIDDLEWARE_PIPELINE_LABELS,
  getMiddlewarePipelineLabel,
  MIDDLEWARE_FLAG_KEYS,
  getAllMiddlewareFlags,
} from "./middleware";
export type { MiddlewareFlagKey } from "./middleware";

// Agent 类型
export { AGENT_TYPE_LABELS, getAgentTypeLabel } from "./agent-types";

// 工具名称
export { TOOL_NAME_LABELS, getToolNameLabel } from "./tools";

// 工具策略字段
export { TOOL_POLICY_FIELD_LABELS, getToolPolicyFieldLabel, type ToolPolicyFieldInfo } from "./tool-policies";

// 策略配置项
export { POLICY_FIELD_LABELS, getPolicyFieldLabel } from "./policies";

// 提示词层级
export { PROMPT_LAYER_LABELS, getPromptLayerLabel } from "./prompt-layers";

// 路由策略
export { ROUTING_POLICY_LABELS, getRoutingPolicyLabel } from "./routing";

// 配置来源
export { CONFIG_SOURCE_LABELS, getConfigSourceLabel } from "./config-sources";

// 知识源类型
export { KNOWLEDGE_TYPE_LABELS, getKnowledgeTypeLabel } from "./knowledge-types";
