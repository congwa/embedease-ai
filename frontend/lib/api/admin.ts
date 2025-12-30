// 管理后台 API

import { apiRequest } from "./client";

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
  return apiRequest<DashboardStats>("/admin/stats");
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
    `/admin/products?${searchParams.toString()}`
  );
}

// 获取会话列表
export async function getConversations(params: {
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
    `/admin/conversations?${searchParams.toString()}`
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
    `/admin/users?${searchParams.toString()}`
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
    `/admin/crawl-tasks?${searchParams.toString()}`
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
    `/admin/crawl-pages?${searchParams.toString()}`
  );
}

// 获取分类列表
export async function getCategories(): Promise<string[]> {
  return apiRequest<string[]>("/admin/categories");
}

// 获取品牌列表
export async function getBrands(): Promise<string[]> {
  return apiRequest<string[]>("/admin/brands");
}
