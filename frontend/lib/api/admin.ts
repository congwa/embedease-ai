// 管理后台 API

import { apiRequest } from "./client";

export interface AgentStatsInfo {
  total_agents: number;
  enabled_agents: number;
  default_agent_id: string | null;
  default_agent_name: string | null;
}

export interface DashboardStats {
  total_products: number;
  total_conversations: number;
  total_users: number;
  total_messages: number;
  total_crawl_sites: number;
  total_crawl_tasks: number;
  crawl_success_rate: number;
  today_conversations: number;
  today_messages: number;
  ai_conversations: number;
  pending_conversations: number;
  human_conversations: number;
  agent_stats: AgentStatsInfo | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProductListItem {
  id: string;
  name: string;
  summary: string | null;
  price: number | null;
  category: string | null;
  brand: string | null;
  source_site_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationListItem {
  id: string;
  user_id: string;
  title: string;
  handoff_state: string;
  handoff_operator: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface UserListItem {
  id: string;
  conversation_count: number;
  created_at: string;
}

export interface CrawlTaskListItem {
  id: number;
  site_id: string;
  site_name: string | null;
  status: string;
  pages_crawled: number;
  pages_parsed: number;
  pages_failed: number;
  products_found: number;
  products_created: number;
  products_updated: number;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface CrawlPageListItem {
  id: number;
  site_id: string;
  task_id: number | null;
  url: string;
  depth: number;
  status: string;
  is_product_page: boolean | null;
  product_id: string | null;
  parse_error: string | null;
  crawled_at: string;
  parsed_at: string | null;
}

// 获取仪表盘统计
export async function getDashboardStats(): Promise<DashboardStats> {
  return apiRequest<DashboardStats>("/api/v1/admin/stats");
}

// 获取商品列表
export async function getProducts(params: {
  page?: number;
  page_size?: number;
  category?: string;
  brand?: string;
  search?: string;
}): Promise<PaginatedResponse<ProductListItem>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.category) searchParams.set("category", params.category);
  if (params.brand) searchParams.set("brand", params.brand);
  if (params.search) searchParams.set("search", params.search);
  return apiRequest<PaginatedResponse<ProductListItem>>(
    `/api/v1/admin/products?${searchParams.toString()}`
  );
}

// 获取会话列表（管理端）
export async function getAdminConversations(params: {
  page?: number;
  page_size?: number;
  handoff_state?: string;
  user_id?: string;
}): Promise<PaginatedResponse<ConversationListItem>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.handoff_state) searchParams.set("handoff_state", params.handoff_state);
  if (params.user_id) searchParams.set("user_id", params.user_id);
  return apiRequest<PaginatedResponse<ConversationListItem>>(
    `/api/v1/admin/conversations?${searchParams.toString()}`
  );
}

// 获取用户列表
export async function getUsers(params: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<UserListItem>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  return apiRequest<PaginatedResponse<UserListItem>>(
    `/api/v1/admin/users?${searchParams.toString()}`
  );
}

// 获取爬取任务列表
export async function getCrawlTasks(params: {
  page?: number;
  page_size?: number;
  site_id?: string;
  status?: string;
}): Promise<PaginatedResponse<CrawlTaskListItem>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.site_id) searchParams.set("site_id", params.site_id);
  if (params.status) searchParams.set("status", params.status);
  return apiRequest<PaginatedResponse<CrawlTaskListItem>>(
    `/api/v1/admin/crawl-tasks?${searchParams.toString()}`
  );
}

// 获取爬取页面列表
export async function getCrawlPages(params: {
  page?: number;
  page_size?: number;
  site_id?: string;
  task_id?: number;
  status?: string;
}): Promise<PaginatedResponse<CrawlPageListItem>> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.site_id) searchParams.set("site_id", params.site_id);
  if (params.task_id) searchParams.set("task_id", String(params.task_id));
  if (params.status) searchParams.set("status", params.status);
  return apiRequest<PaginatedResponse<CrawlPageListItem>>(
    `/api/v1/admin/crawl-pages?${searchParams.toString()}`
  );
}

// 获取分类列表
export async function getCategories(): Promise<string[]> {
  return apiRequest<string[]>("/api/v1/admin/categories");
}

// 获取品牌列表
export async function getBrands(): Promise<string[]> {
  return apiRequest<string[]>("/api/v1/admin/brands");
}

// Supervisor 全局配置（只读，从 admin 接口）
export interface SupervisorConfig {
  enabled: boolean;
  default_agent_id: string | null;
  default_agent_name: string | null;
  intent_timeout: number;
  allow_multi_agent: boolean;
  supervisor_agents: Array<{
    id: string;
    name: string;
    description: string | null;
    sub_agent_count: number;
    is_default: boolean;
  }>;
}

// 获取 Supervisor 全局配置（只读）
export async function getSupervisorConfig(): Promise<SupervisorConfig> {
  return apiRequest<SupervisorConfig>("/api/v1/admin/settings/supervisor");
}

// Supervisor 子 Agent 配置
export interface SupervisorSubAgent {
  agent_id: string;
  name: string;
  description: string | null;
  routing_hints: string[];
  priority: number;
}

// Supervisor 路由规则
export interface SupervisorRoutingRule {
  condition_type: string;
  keywords: string[];
  intents: string[];
  target_agent_id: string;
  priority: number;
}

// Supervisor 路由策略
export interface SupervisorRoutingPolicy {
  type: string;
  rules: SupervisorRoutingRule[];
  default_agent_id: string | null;
}

// 全局 Supervisor 配置
export interface SupervisorGlobalConfig {
  enabled: boolean;
  supervisor_prompt: string | null;
  sub_agents: SupervisorSubAgent[];
  routing_policy: SupervisorRoutingPolicy;
  intent_timeout: number;
  allow_multi_agent: boolean;
  source: string;
}

export interface SupervisorGlobalConfigUpdate {
  enabled?: boolean;
  supervisor_prompt?: string | null;
  sub_agents?: SupervisorSubAgent[];
  routing_policy?: SupervisorRoutingPolicy;
  intent_timeout?: number;
  allow_multi_agent?: boolean;
}

// 可选为子 Agent 的 Agent
export interface AvailableAgentForSupervisor {
  id: string;
  name: string;
  description: string | null;
  type: string;
  status: string;
  is_selected: boolean;
}

// 获取全局 Supervisor 配置
export async function getSupervisorGlobalConfig(): Promise<SupervisorGlobalConfig> {
  return apiRequest<SupervisorGlobalConfig>("/api/v1/admin/system-config/supervisor");
}

// 更新全局 Supervisor 配置
export async function updateSupervisorGlobalConfig(
  data: SupervisorGlobalConfigUpdate
): Promise<SupervisorGlobalConfig> {
  return apiRequest<SupervisorGlobalConfig>("/api/v1/admin/system-config/supervisor", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// 获取可选子 Agent 列表
export async function getAvailableAgentsForSupervisor(): Promise<AvailableAgentForSupervisor[]> {
  return apiRequest<AvailableAgentForSupervisor[]>("/api/v1/admin/system-config/supervisor/available-agents");
}

// 添加子 Agent
export async function addSubAgent(data: SupervisorSubAgent): Promise<SupervisorGlobalConfig> {
  return apiRequest<SupervisorGlobalConfig>("/api/v1/admin/system-config/supervisor/sub-agents", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// 移除子 Agent
export async function removeSubAgent(agentId: string): Promise<SupervisorGlobalConfig> {
  return apiRequest<SupervisorGlobalConfig>(`/api/v1/admin/system-config/supervisor/sub-agents/${agentId}`, {
    method: "DELETE",
  });
}
