// 客服支持 API

import { apiRequest } from "./client";
import type { ImageAttachment } from "@/types/chat";

export interface SupportConversation {
  id: string;
  user_id: string;
  title: string;
  handoff_state: string;
  handoff_operator: string | null;
  user_online: boolean;
  updated_at: string;
  created_at: string;
  heat_score: number;  // 热度得分
  unread_count: number;  // 未读消息数
}

export interface SupportStats {
  pending_count: number;  // 等待接入数
  human_count: number;  // 人工服务中数
  total_unread: number;  // 总未读消息数
  high_heat_count: number;  // 高热会话数
}

export interface SupportConversationListResponse {
  items: SupportConversation[];
  total: number;
  offset: number;
  limit: number;
}

export interface ConversationStateResponse {
  conversation_id: string;
  handoff_state: string;
  handoff_operator: string | null;
  handoff_reason: string | null;
  handoff_at: string | null;
  last_notification_at: string | null;
}

export interface HandoffResponse {
  success: boolean;
  conversation_id?: string;
  operator?: string;
  error?: string;
  handoff_at?: string;
  ended_by?: string;
  current_operator?: string;
  handoff_state?: "ai" | "pending" | "human";  // 保底机制：返回最新状态
}

export interface MessageResponse {
  id: string;
  role: string;
  content: string;
  products: string | null;
  message_type?: string;
  extra_metadata?: {
    images?: Array<{
      id: string;
      url: string;
      thumbnail_url?: string;
      filename?: string;
    }>;
    operator?: string;
  } | null;
  created_at: string;
}

export interface ConversationDetailResponse {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  handoff_state?: string;
  handoff_operator?: string | null;
  agent_id?: string;
  messages: MessageResponse[];
}

// 获取会话列表
export async function getSupportConversations(
  state?: string,
  sortBy: "heat" | "time" = "heat",
  limit = 50,
  offset = 0
): Promise<SupportConversationListResponse> {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  params.set("sort_by", sortBy);
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  
  return apiRequest<SupportConversationListResponse>(
    `/api/v1/support/conversations?${params.toString()}`
  );
}

// 获取客服统计数据（用于红点提醒）
export async function getSupportStats(): Promise<SupportStats> {
  return apiRequest<SupportStats>("/api/v1/support/stats");
}

// 获取会话状态
export async function getConversationState(
  conversationId: string
): Promise<ConversationStateResponse> {
  return apiRequest<ConversationStateResponse>(
    `/api/v1/support/handoff/${conversationId}`
  );
}

// 获取会话详情（含历史消息）
export async function getConversationDetail(
  conversationId: string
): Promise<ConversationDetailResponse> {
  return apiRequest<ConversationDetailResponse>(
    `/api/v1/conversations/${conversationId}`
  );
}

// 开始介入
export async function startHandoff(
  conversationId: string,
  operator: string,
  reason?: string
): Promise<HandoffResponse> {
  return apiRequest<HandoffResponse>(
    `/api/v1/support/handoff/${conversationId}`,
    {
      method: "POST",
      body: JSON.stringify({ operator, reason: reason || "" }),
    }
  );
}

// 结束介入
export async function endHandoff(
  conversationId: string,
  operator: string,
  summary?: string
): Promise<HandoffResponse> {
  return apiRequest<HandoffResponse>(
    `/api/v1/support/handoff/${conversationId}/close`,
    {
      method: "POST",
      body: JSON.stringify({ operator, summary: summary || "" }),
    }
  );
}

// 发送客服消息（REST 备用，支持图片）
export async function sendHumanMessage(
  conversationId: string,
  content: string,
  operator: string,
  images?: ImageAttachment[]
): Promise<{ success: boolean; message_id?: string; error?: string }> {
  return apiRequest(
    `/api/v1/support/message/${conversationId}`,
    {
      method: "POST",
      body: JSON.stringify({ content, operator, images }),
    }
  );
}
