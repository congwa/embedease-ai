/**
 * 提示词管理 API 客户端
 */

import { apiRequest } from "@/lib/api/client";

// ========== 类型定义 ==========

export type PromptCategory = "agent" | "memory" | "skill" | "crawler";
export type PromptSource = "default" | "custom";

export interface Prompt {
  key: string;
  category: PromptCategory;
  name: string;
  description: string | null;
  content: string;
  variables: string[];
  source: PromptSource;
  is_active: boolean;
  default_content: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PromptListResponse {
  items: Prompt[];
  total: number;
}

export interface PromptUpdate {
  name?: string;
  description?: string;
  content?: string;
  is_active?: boolean;
}

export interface PromptCreate {
  key: string;
  category: PromptCategory;
  name: string;
  description?: string;
  content: string;
  variables?: string[];
}

export interface PromptResetResponse {
  key: string;
  message: string;
  content: string;
}

// ========== API 函数 ==========

const BASE_URL = "/api/v1/admin/prompts";

/**
 * 获取提示词列表
 */
export async function listPrompts(params?: {
  category?: PromptCategory;
  include_inactive?: boolean;
}): Promise<PromptListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set("category", params.category);
  if (params?.include_inactive) searchParams.set("include_inactive", "true");

  const query = searchParams.toString();
  const url = query ? `${BASE_URL}?${query}` : BASE_URL;
  return apiRequest<PromptListResponse>(url);
}

/**
 * 获取单个提示词
 */
export async function getPrompt(key: string): Promise<Prompt> {
  return apiRequest<Prompt>(`${BASE_URL}/${encodeURIComponent(key)}`);
}

/**
 * 更新提示词
 */
export async function updatePrompt(
  key: string,
  data: PromptUpdate
): Promise<Prompt> {
  return apiRequest<Prompt>(`${BASE_URL}/${encodeURIComponent(key)}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

/**
 * 创建自定义提示词
 */
export async function createPrompt(data: PromptCreate): Promise<Prompt> {
  return apiRequest<Prompt>(BASE_URL, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * 重置提示词为默认值
 */
export async function resetPrompt(key: string): Promise<PromptResetResponse> {
  return apiRequest<PromptResetResponse>(
    `${BASE_URL}/${encodeURIComponent(key)}/reset`,
    {
      method: "POST",
    }
  );
}

/**
 * 删除自定义提示词
 */
export async function deletePrompt(key: string): Promise<void> {
  await apiRequest<void>(`${BASE_URL}/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
}

// ========== 辅助函数 ==========

export const PROMPT_CATEGORY_LABELS: Record<PromptCategory, string> = {
  agent: "Agent 提示词",
  memory: "记忆系统",
  skill: "技能生成",
  crawler: "爬虫提取",
};

export const PROMPT_CATEGORY_COLORS: Record<PromptCategory, string> = {
  agent: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  memory: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  skill: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  crawler: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300",
};

export const PROMPT_SOURCE_LABELS: Record<PromptSource, string> = {
  default: "默认",
  custom: "已自定义",
};
