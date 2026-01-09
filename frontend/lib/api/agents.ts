// Agent 管理 API

import { apiRequest } from "./client";

// ========== Types ==========

export interface GreetingCTA {
  text: string;
  payload: string;
}

export interface GreetingChannel {
  title?: string;
  subtitle?: string;
  body: string;
  cta?: GreetingCTA;
}

export interface GreetingConfig {
  enabled: boolean;
  trigger: "first_visit" | "every_session";
  delay_ms: number;
  channels: Record<string, GreetingChannel>;
  cta?: GreetingCTA;
  variables?: string[];
}

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  type: "product" | "faq" | "kb" | "custom";
  system_prompt: string;
  mode_default: "natural" | "free" | "strict";
  middleware_flags: Record<string, boolean> | null;
  tool_policy: Record<string, unknown> | null;
  tool_categories: string[] | null;
  knowledge_config_id: string | null;
  response_format: string | null;
  status: "enabled" | "disabled";
  is_default: boolean;
  greeting_config: GreetingConfig | null;
  created_at: string;
  updated_at: string;
  knowledge_config: KnowledgeConfig | null;
}

export interface AgentListResponse {
  items: Agent[];
  total: number;
}

export interface KnowledgeConfig {
  id: string;
  name: string;
  type: "faq" | "vector" | "graph" | "product" | "http_api" | "mixed";
  index_name: string | null;
  collection_name: string | null;
  embedding_model: string | null;
  top_k: number;
  similarity_threshold: number | null;
  rerank_enabled: boolean;
  filters: Record<string, unknown> | null;
  data_version: string | null;
  fingerprint: string | null;
  created_at: string;
  updated_at: string;
}

export interface FAQEntry {
  id: string;
  agent_id: string | null;
  question: string;
  answer: string;
  category: string | null;
  tags: string[] | null;
  source: string | null;
  priority: number;
  enabled: boolean;
  vector_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface FAQImportResponse {
  imported_count: number;
  skipped_count: number;
  errors: string[];
}

export interface FAQUpsertResponse extends FAQEntry {
  merged: boolean;
  target_id: string | null;
  similarity_score: number | null;
}

export interface FAQCategoryStats {
  name: string;
  count: number;
}

export interface FAQRecentUpdate {
  id: string;
  question: string;
  source: string | null;
  updated_at: string;
}

export interface FAQStatsResponse {
  total: number;
  enabled: number;
  disabled: number;
  unindexed: number;
  categories: FAQCategoryStats[];
  recent_updates: FAQRecentUpdate[];
}

export interface FAQListParams {
  skip?: number;
  limit?: number;
  agent_id?: string;
  category?: string;
  source?: string;
  enabled?: boolean;
  priority_min?: number;
  priority_max?: number;
  tags?: string;
  order_by?: "priority_desc" | "priority_asc" | "updated_desc" | "updated_asc" | "unindexed_first";
}

export interface SettingsOverview {
  llm_provider: string;
  llm_model: string;
  llm_base_url: string;
  llm_api_key_masked: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dimension: number;
  embedding_base_url: string | null;
  rerank_enabled: boolean;
  rerank_provider: string | null;
  rerank_model: string | null;
  memory_enabled: boolean;
  memory_store_enabled: boolean;
  memory_fact_enabled: boolean;
  memory_graph_enabled: boolean;
  agent_todo_enabled: boolean;
  agent_tool_limit_enabled: boolean;
  agent_tool_retry_enabled: boolean;
  agent_summarization_enabled: boolean;
  crawler_enabled: boolean;
  database_path: string;
  checkpoint_db_path: string;
  qdrant_host: string;
  qdrant_port: number;
  qdrant_collection: string;
  // MinIO 存储配置
  minio_enabled: boolean;
  minio_endpoint: string | null;
  minio_bucket: string | null;
  image_max_size_mb: number;
  image_max_count: number;
}

export interface MiddlewareDefaults {
  todo_enabled: boolean;
  tool_limit_enabled: boolean;
  tool_limit_run: number | null;
  tool_limit_thread: number | null;
  tool_retry_enabled: boolean;
  tool_retry_max_retries: number;
  summarization_enabled: boolean;
  summarization_trigger_messages: number;
  summarization_keep_messages: number;
}

// ========== Agent API ==========

export async function getAgents(params?: {
  skip?: number;
  limit?: number;
  status_filter?: string;
  type_filter?: string;
}): Promise<AgentListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set("skip", String(params.skip));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.status_filter) searchParams.set("status_filter", params.status_filter);
  if (params?.type_filter) searchParams.set("type_filter", params.type_filter);
  const query = searchParams.toString();
  return apiRequest<AgentListResponse>(`/api/v1/admin/agents${query ? `?${query}` : ""}`);
}

export async function getAgent(agentId: string): Promise<Agent> {
  return apiRequest<Agent>(`/api/v1/admin/agents/${agentId}`);
}

export async function createAgent(data: Partial<Agent>): Promise<Agent> {
  return apiRequest<Agent>("/api/v1/admin/agents", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateAgent(agentId: string, data: Partial<Agent>): Promise<Agent> {
  return apiRequest<Agent>(`/api/v1/admin/agents/${agentId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAgent(agentId: string): Promise<void> {
  await apiRequest(`/api/v1/admin/agents/${agentId}`, {
    method: "DELETE",
  });
}

export async function refreshAgent(agentId: string): Promise<void> {
  await apiRequest(`/api/v1/admin/agents/${agentId}/refresh`, {
    method: "POST",
  });
}

// ========== Greeting Config API ==========

export async function getAgentGreeting(agentId: string): Promise<GreetingConfig | null> {
  return apiRequest<GreetingConfig | null>(`/api/v1/admin/agents/${agentId}/greeting`);
}

export async function updateAgentGreeting(
  agentId: string,
  data: Partial<GreetingConfig>
): Promise<GreetingConfig> {
  return apiRequest<GreetingConfig>(`/api/v1/admin/agents/${agentId}/greeting`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

// ========== Knowledge Config API ==========

export async function getKnowledgeConfigs(params?: {
  skip?: number;
  limit?: number;
}): Promise<KnowledgeConfig[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set("skip", String(params.skip));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  return apiRequest<KnowledgeConfig[]>(`/api/v1/admin/knowledge-configs${query ? `?${query}` : ""}`);
}

export async function getKnowledgeConfig(configId: string): Promise<KnowledgeConfig> {
  return apiRequest<KnowledgeConfig>(`/api/v1/admin/knowledge-configs/${configId}`);
}

export async function createKnowledgeConfig(data: Partial<KnowledgeConfig>): Promise<KnowledgeConfig> {
  return apiRequest<KnowledgeConfig>("/api/v1/admin/knowledge-configs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateKnowledgeConfig(configId: string, data: Partial<KnowledgeConfig>): Promise<KnowledgeConfig> {
  return apiRequest<KnowledgeConfig>(`/api/v1/admin/knowledge-configs/${configId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteKnowledgeConfig(configId: string): Promise<void> {
  await apiRequest(`/api/v1/admin/knowledge-configs/${configId}`, {
    method: "DELETE",
  });
}

// ========== FAQ API ==========

export async function getFAQEntries(params?: FAQListParams): Promise<FAQEntry[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set("skip", String(params.skip));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.agent_id) searchParams.set("agent_id", params.agent_id);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.source) searchParams.set("source", params.source);
  if (params?.enabled !== undefined) searchParams.set("enabled", String(params.enabled));
  if (params?.priority_min !== undefined) searchParams.set("priority_min", String(params.priority_min));
  if (params?.priority_max !== undefined) searchParams.set("priority_max", String(params.priority_max));
  if (params?.tags) searchParams.set("tags", params.tags);
  if (params?.order_by) searchParams.set("order_by", params.order_by);
  const query = searchParams.toString();
  return apiRequest<FAQEntry[]>(`/api/v1/admin/faq${query ? `?${query}` : ""}`);
}

export async function getFAQStats(agentId: string): Promise<FAQStatsResponse> {
  return apiRequest<FAQStatsResponse>(`/api/v1/admin/faq/stats?agent_id=${agentId}`);
}

export async function getFAQEntry(entryId: string): Promise<FAQEntry> {
  return apiRequest<FAQEntry>(`/api/v1/admin/faq/${entryId}`);
}

export async function createFAQEntry(
  data: Partial<FAQEntry>,
  autoMerge: boolean = true
): Promise<FAQUpsertResponse> {
  const searchParams = new URLSearchParams();
  searchParams.set("auto_merge", String(autoMerge));
  return apiRequest<FAQUpsertResponse>(`/api/v1/admin/faq?${searchParams.toString()}`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateFAQEntry(entryId: string, data: Partial<FAQEntry>): Promise<FAQEntry> {
  return apiRequest<FAQEntry>(`/api/v1/admin/faq/${entryId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteFAQEntry(entryId: string): Promise<void> {
  await apiRequest(`/api/v1/admin/faq/${entryId}`, {
    method: "DELETE",
  });
}

export async function importFAQ(data: {
  agent_id?: string;
  entries: Array<{
    question: string;
    answer: string;
    category?: string;
    tags?: string[];
    source?: string;
    priority?: number;
    enabled?: boolean;
  }>;
  rebuild_index?: boolean;
}): Promise<FAQImportResponse> {
  return apiRequest<FAQImportResponse>("/api/v1/admin/faq/import", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function rebuildFAQIndex(agentId?: string): Promise<void> {
  const searchParams = new URLSearchParams();
  if (agentId) searchParams.set("agent_id", agentId);
  const query = searchParams.toString();
  await apiRequest(`/api/v1/admin/faq/rebuild-index${query ? `?${query}` : ""}`, {
    method: "POST",
  });
}

export async function exportFAQEntries(params?: {
  agent_id?: string;
  category?: string;
  enabled?: boolean;
}): Promise<FAQEntry[]> {
  const searchParams = new URLSearchParams();
  if (params?.agent_id) searchParams.set("agent_id", params.agent_id);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.enabled !== undefined) searchParams.set("enabled", String(params.enabled));
  const query = searchParams.toString();
  return apiRequest<FAQEntry[]>(`/api/v1/admin/faq/export${query ? `?${query}` : ""}`);
}

// ========== Settings API ==========

export async function getSettingsOverview(): Promise<SettingsOverview> {
  return apiRequest<SettingsOverview>("/api/v1/admin/settings/overview");
}

export async function getMiddlewareDefaults(): Promise<MiddlewareDefaults> {
  return apiRequest<MiddlewareDefaults>("/api/v1/admin/settings/middleware-defaults");
}

export async function getRawConfig(): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>("/api/v1/admin/settings/raw-config");
}

// ========== Memory Config API ==========

export interface MemoryConfig {
  inject_profile: boolean;
  inject_facts: boolean;
  inject_graph: boolean;
  max_facts: number;
  max_graph_entities: number;
  memory_enabled: boolean;
  store_enabled: boolean;
  fact_enabled: boolean;
  graph_enabled: boolean;
}

export interface PromptPreviewRequest {
  user_id?: string;
  mode?: string;
}

export interface PromptPreviewResponse {
  base_prompt: string;
  mode_suffix: string;
  memory_context: string;
  full_prompt: string;
}

export interface AgentUserItem {
  user_id: string;
  conversation_count: number;
  last_active: string | null;
}

export interface AgentUsersResponse {
  total: number;
  items: AgentUserItem[];
}

export async function getAgentMemoryConfig(agentId: string): Promise<MemoryConfig> {
  return apiRequest<MemoryConfig>(`/api/v1/admin/agents/${agentId}/memory-config`);
}

export async function previewAgentPrompt(
  agentId: string,
  data: PromptPreviewRequest
): Promise<PromptPreviewResponse> {
  return apiRequest<PromptPreviewResponse>(`/api/v1/admin/agents/${agentId}/preview-prompt`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAgentUsers(
  agentId: string,
  limit?: number
): Promise<AgentUsersResponse> {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set("limit", String(limit));
  const query = searchParams.toString();
  return apiRequest<AgentUsersResponse>(
    `/api/v1/admin/agents/${agentId}/users${query ? `?${query}` : ""}`
  );
}
