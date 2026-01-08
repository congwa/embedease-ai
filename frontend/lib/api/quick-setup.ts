// Quick Setup 快捷配置中心 API

import { apiRequest } from "./client";

// ========== Types ==========

export type SetupStepStatus = "pending" | "in_progress" | "completed" | "skipped";
export type ChecklistItemStatus = "ok" | "default" | "missing" | "error";

export interface SetupStep {
  index: number;
  key: string;
  title: string;
  description: string | null;
  status: SetupStepStatus;
  data: Record<string, unknown> | null;
}

export interface QuickSetupState {
  completed: boolean;
  current_step: number;
  steps: SetupStep[];
  agent_id: string | null;
  updated_at: string | null;
}

export interface ChecklistItem {
  key: string;
  label: string;
  category: string;
  status: ChecklistItemStatus;
  current_value: string | null;
  default_value: string | null;
  description: string | null;
  step_index: number | null;
}

export interface ChecklistResponse {
  items: ChecklistItem[];
  total: number;
  ok_count: number;
  default_count: number;
  missing_count: number;
}

export interface AgentTypeField {
  key: string;
  label: string;
  type: "text" | "textarea" | "select" | "multiselect" | "switch" | "number";
  required: boolean;
  default: unknown;
  options: Array<{ value: string; label: string }> | null;
  description: string | null;
  group: string | null;
}

export interface AgentTypeStepConfig {
  step_key: string;
  enabled: boolean;
  title_override: string | null;
  description_override: string | null;
  fields: AgentTypeField[];
  hints: string[];
}

export interface AgentTypeConfig {
  type: "product" | "faq" | "kb" | "custom";
  name: string;
  description: string;
  icon: string;
  default_tool_categories: string[];
  default_middleware_flags: Record<string, boolean>;
  default_knowledge_type: string | null;
  steps: AgentTypeStepConfig[];
  greeting_template: Record<string, unknown> | null;
  system_prompt_template: string | null;
}

export interface ServiceHealthItem {
  name: string;
  status: "ok" | "error" | "unknown";
  message: string | null;
  latency_ms: number | null;
}

export interface HealthCheckResponse {
  services: ServiceHealthItem[];
  all_ok: boolean;
}

export interface QuickStats {
  agents: {
    total: number;
    default_id: string | null;
    default_name: string | null;
    default_type: string | null;
  };
  faq: {
    total: number;
    unindexed: number;
  };
  knowledge_configs: {
    total: number;
  };
  settings: {
    llm_provider: string;
    llm_model: string;
    embedding_model: string;
    qdrant_collection: string;
    memory_enabled: boolean;
    crawler_enabled: boolean;
  };
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

// ========== State API ==========

export async function getSetupState(): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>("/api/v1/admin/quick-setup/state");
}

export async function updateSetupState(
  data: Partial<QuickSetupState>
): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>("/api/v1/admin/quick-setup/state", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function resetSetupState(): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>("/api/v1/admin/quick-setup/state/reset", {
    method: "POST",
  });
}

export async function completeStep(
  stepIndex: number,
  data?: Record<string, unknown>
): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>(
    `/api/v1/admin/quick-setup/state/step/${stepIndex}/complete`,
    {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }
  );
}

export async function skipStep(stepIndex: number): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>(
    `/api/v1/admin/quick-setup/state/step/${stepIndex}/skip`,
    {
      method: "POST",
    }
  );
}

export async function gotoStep(stepIndex: number): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>(
    `/api/v1/admin/quick-setup/state/step/${stepIndex}/goto`,
    {
      method: "POST",
    }
  );
}

export async function setCurrentAgent(agentId: string): Promise<QuickSetupState> {
  return apiRequest<QuickSetupState>(
    `/api/v1/admin/quick-setup/state/agent/${agentId}`,
    {
      method: "POST",
    }
  );
}

// ========== Checklist API ==========

export async function getChecklist(): Promise<ChecklistResponse> {
  return apiRequest<ChecklistResponse>("/api/v1/admin/quick-setup/checklist");
}

export async function getChecklistSummary(): Promise<Record<string, Record<string, number>>> {
  return apiRequest<Record<string, Record<string, number>>>(
    "/api/v1/admin/quick-setup/checklist/summary"
  );
}

// ========== Agent Type API ==========

export async function getAgentTypes(): Promise<AgentTypeConfig[]> {
  const response = await apiRequest<{ items: AgentTypeConfig[] }>(
    "/api/v1/admin/quick-setup/agent-types"
  );
  return response.items;
}

export async function getAgentTypeConfig(
  agentType: string
): Promise<AgentTypeConfig> {
  return apiRequest<AgentTypeConfig>(
    `/api/v1/admin/quick-setup/agent-types/${agentType}`
  );
}

export async function getAgentTypeDefaults(
  agentType: string
): Promise<{
  tool_categories: string[];
  middleware_flags: Record<string, boolean>;
  knowledge_type: string | null;
  system_prompt_template: string | null;
  greeting_template: Record<string, unknown> | null;
}> {
  return apiRequest(`/api/v1/admin/quick-setup/agent-types/${agentType}/defaults`);
}

// ========== Health & Stats API ==========

export async function checkServicesHealth(): Promise<HealthCheckResponse> {
  return apiRequest<HealthCheckResponse>("/api/v1/admin/quick-setup/health");
}

export async function getQuickStats(): Promise<QuickStats> {
  return apiRequest<QuickStats>("/api/v1/admin/quick-setup/stats");
}

// ========== Validation API ==========

export async function validateStep(
  stepKey: string,
  data: Record<string, unknown>,
  agentType?: string
): Promise<ValidationResult> {
  const params = new URLSearchParams();
  if (agentType) params.set("agent_type", agentType);
  const query = params.toString();
  return apiRequest<ValidationResult>(
    `/api/v1/admin/quick-setup/validate/${stepKey}${query ? `?${query}` : ""}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}
