/**
 * Agent 运行态配置相关类型
 */

export interface PromptLayer {
  name: string;
  source: string;
  char_count: number;
  content?: string;
  skill_ids?: string[];
}

export interface EffectiveSystemPrompt {
  final_content: string;
  char_count: number;
  layers: PromptLayer[];
}

export interface SkillInfo {
  id: string;
  name: string;
  description?: string;
  priority: number;
  content_preview?: string;
  trigger_keywords: string[];
}

export interface EffectiveSkills {
  always_apply: SkillInfo[];
  conditional: SkillInfo[];
  triggered_by_test_message?: string[];
}

export interface ToolInfo {
  name: string;
  description: string;
  categories: string[];
  sources: string[];
}

export interface FilteredToolInfo {
  name: string;
  reason: string;
}

export interface EffectiveTools {
  enabled: ToolInfo[];
  filtered: FilteredToolInfo[];
}

export interface MiddlewareInfo {
  name: string;
  order: number;
  enabled: boolean;
  source: string;
  reason?: string | null;
  params: Record<string, unknown>;
}

export interface EffectiveMiddlewares {
  pipeline: MiddlewareInfo[];
  disabled: MiddlewareInfo[];
}

export interface EffectiveKnowledge {
  configured: boolean;
  type?: string | null;
  name?: string | null;
  index_name?: string | null;
  collection_name?: string | null;
  embedding_model?: string | null;
  top_k?: number | null;
  similarity_threshold?: number | null;
  rerank_enabled: boolean;
  data_version?: string | null;
}

export interface PolicyValue {
  value: unknown;
  source: string;
}

export interface EffectiveToolPolicy {
  min_tool_calls: PolicyValue;
  allow_direct_answer: PolicyValue;
  fallback_tool?: PolicyValue | null;
  clarification_tool?: PolicyValue | null;
}

export interface EffectivePolicies {
  mode: string;
  tool_policy?: EffectiveToolPolicy | null;
  middleware_flags: Record<string, PolicyValue>;
}

export interface EffectiveHealth {
  score: number;
  warnings: string[];
  passed: string[];
}

export interface EffectiveConfigResponse {
  agent_id: string;
  name: string;
  type: string;
  mode: string;
  config_version: string;
  generated_at: string;
  system_prompt: EffectiveSystemPrompt;
  skills: EffectiveSkills;
  tools: EffectiveTools;
  middlewares: EffectiveMiddlewares;
  knowledge: EffectiveKnowledge;
  policies: EffectivePolicies;
  health: EffectiveHealth;
}

export interface EffectiveConfigParams {
  mode?: string;
  include_filtered?: boolean;
  test_message?: string;
}
