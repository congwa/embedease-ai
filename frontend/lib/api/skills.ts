/**
 * 技能管理 API 客户端
 */

import { apiRequest } from "@/lib/api/client";

// ========== 类型定义 ==========

export type SkillType = "system" | "user" | "ai";
export type SkillCategory = "prompt" | "retrieval" | "tool" | "workflow";

export interface Skill {
  id: string;
  name: string;
  description: string;
  category: SkillCategory;
  content: string;
  trigger_keywords: string[];
  trigger_intents: string[];
  always_apply: boolean;
  applicable_agents: string[];
  type: SkillType;
  version: string;
  author: string | null;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface SkillListResponse {
  items: Skill[];
  total: number;
  page: number;
  page_size: number;
}

export interface SkillCreate {
  name: string;
  description: string;
  category?: SkillCategory;
  content: string;
  trigger_keywords?: string[];
  trigger_intents?: string[];
  always_apply?: boolean;
  applicable_agents?: string[];
}

export interface SkillUpdate {
  name?: string;
  description?: string;
  category?: SkillCategory;
  content?: string;
  trigger_keywords?: string[];
  trigger_intents?: string[];
  always_apply?: boolean;
  applicable_agents?: string[];
  is_active?: boolean;
}

export interface SkillGenerateRequest {
  description: string;
  category?: SkillCategory;
  applicable_agents?: string[];
  examples?: string[];
}

export interface SkillGenerateResponse {
  skill: SkillCreate;
  confidence: number;
  suggestions: string[];
}

export interface AgentSkillConfig {
  skill_id: string;
  priority: number;
  is_enabled: boolean;
}

export interface AgentSkillRead {
  skill_id: string;
  skill_name: string;
  skill_description: string;
  priority: number;
  is_enabled: boolean;
}

// ========== API 函数 ==========

const BASE_URL = "/api/v1/admin/skills";

/**
 * 获取技能列表
 */
export async function listSkills(params?: {
  type?: SkillType;
  category?: SkillCategory;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}): Promise<SkillListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.type) searchParams.set("type", params.type);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.is_active !== undefined)
    searchParams.set("is_active", String(params.is_active));
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));

  const query = searchParams.toString();
  const url = query ? `${BASE_URL}?${query}` : BASE_URL;
  return apiRequest<SkillListResponse>(url);
}

/**
 * 获取技能详情
 */
export async function getSkill(skillId: string): Promise<Skill> {
  return apiRequest<Skill>(`${BASE_URL}/${skillId}`);
}

/**
 * 创建技能
 */
export async function createSkill(data: SkillCreate): Promise<Skill> {
  return apiRequest<Skill>(BASE_URL, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * 更新技能
 */
export async function updateSkill(
  skillId: string,
  data: SkillUpdate
): Promise<Skill> {
  return apiRequest<Skill>(`${BASE_URL}/${skillId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/**
 * 删除技能
 */
export async function deleteSkill(skillId: string): Promise<void> {
  await apiRequest<void>(`${BASE_URL}/${skillId}`, {
    method: "DELETE",
  });
}

/**
 * AI 生成技能
 */
export async function generateSkill(
  data: SkillGenerateRequest
): Promise<SkillGenerateResponse> {
  return apiRequest<SkillGenerateResponse>(`${BASE_URL}/generate`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * AI 优化技能
 */
export async function refineSkill(
  skillId: string,
  feedback: string
): Promise<SkillGenerateResponse> {
  return apiRequest<SkillGenerateResponse>(`${BASE_URL}/${skillId}/refine`, {
    method: "POST",
    body: JSON.stringify({ feedback }),
  });
}

/**
 * 获取 Agent 的技能列表
 */
export async function getAgentSkills(
  agentId: string
): Promise<AgentSkillRead[]> {
  return apiRequest<AgentSkillRead[]>(`${BASE_URL}/agents/${agentId}`);
}

/**
 * 更新 Agent 的技能配置
 */
export async function updateAgentSkills(
  agentId: string,
  skills: AgentSkillConfig[]
): Promise<void> {
  await apiRequest<void>(`${BASE_URL}/agents/${agentId}`, {
    method: "PUT",
    body: JSON.stringify({ skills }),
  });
}

/**
 * 获取系统技能列表
 */
export async function getSystemSkills(): Promise<Skill[]> {
  return apiRequest<Skill[]>(`${BASE_URL}/system/list`);
}

/**
 * 初始化系统技能
 */
export async function initSystemSkills(): Promise<{ created: number }> {
  return apiRequest<{ created: number }>(`${BASE_URL}/system/init`, {
    method: "POST",
  });
}

/**
 * 重新加载技能缓存
 */
export async function reloadSkillCache(): Promise<void> {
  await apiRequest<void>(`${BASE_URL}/cache/reload`, {
    method: "POST",
  });
}

/**
 * 清除技能缓存
 */
export async function clearSkillCache(): Promise<void> {
  await apiRequest<void>(`${BASE_URL}/cache`, {
    method: "DELETE",
  });
}

// ========== 辅助函数 ==========

export const SKILL_TYPE_LABELS: Record<SkillType, string> = {
  system: "系统内置",
  user: "用户创建",
  ai: "AI 生成",
};

export const SKILL_CATEGORY_LABELS: Record<SkillCategory, string> = {
  prompt: "提示词增强",
  retrieval: "检索增强",
  tool: "工具扩展",
  workflow: "工作流",
};

export const AGENT_TYPE_OPTIONS = [
  { value: "product", label: "商品推荐" },
  { value: "faq", label: "FAQ" },
  { value: "knowledge", label: "知识库" },
  { value: "support", label: "客服" },
];

