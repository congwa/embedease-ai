// 客服支持 API

import { apiRequest } from "./client";
import type { ImageAttachment } from "@/types/chat";

export interface TicketSummary {
  id: string;
  status: string;
  primary_issue_tag: string | null;
  secondary_issue_tags: string[];
  current_agent_tag: string | null;
  priority_level: string | null;
  risk_level: string | null;
  unresolved_turns: number;
  handoff_required: boolean;
  handoff_reason: string | null;
  merged_from_latest_message: boolean;
  secondary_issue_detected: boolean;
  updated_at: string | null;
}

export interface ReviewSummary {
  status: string;
  score: number | null;
  risk_level: string | null;
  reasons: string[];
  suggested_next_agent: string | null;
  created_at: string | null;
}

export interface RecentTaskSummary {
  id: string;
  ticket_id: string;
  task_type: string;
  agent_tag: string;
  status: string;
  goal: string | null;
  success_criteria: string[];
  review_required: boolean;
  review_status: string | null;
  business_summary: string | null;
  failure_reason: string | null;
  output_payload: Record<string, unknown> | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface SecondaryIssueSummary {
  issue_tag: string;
  reason: string | null;
  raw_message: string | null;
  extra_data: Record<string, unknown>;
}

export interface TicketTimelineEntry {
  event_type: string;
  summary: string;
  extra: Record<string, unknown>;
  created_at: string | null;
}

export interface TicketDetail {
  id: string;
  conversation_id: string;
  user_id: string;
  status: string;
  is_primary_active: boolean;
  parent_ticket_id: string | null;
  superseded_by_ticket_id: string | null;
  issue_fingerprint: string | null;
  primary_issue_tag: string | null;
  secondary_issue_tags: string[];
  secondary_issues: SecondaryIssueSummary[];
  sentiment: string | null;
  severity: string | null;
  priority_level: string | null;
  risk_level: string | null;
  current_agent_tag: string | null;
  current_task_id: string | null;
  current_node_key: string | null;
  unresolved_turns: number;
  rework_count: number;
  handoff_required: boolean;
  handoff_reason: string | null;
  handoff_summary: Record<string, unknown> | null;
  resolved_summary: string | null;
  slot_data: Record<string, unknown>;
  timeline: TicketTimelineEntry[];
  version: number;
  latest_review: ReviewSummary | null;
  recent_tasks: RecentTaskSummary[];
  created_at: string | null;
  updated_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface ConversationTicketsResponse {
  conversation_id: string;
  items: TicketSummary[];
  total: number;
}

export interface TicketActionResponse {
  success: boolean;
  ticket: TicketDetail | null;
  error?: string | null;
}

export interface SupportConversation {
  id: string;
  user_id: string;
  title: string;
  conversation_mode?: string | null;
  handoff_state: string;
  handoff_operator: string | null;
  handoff_reason?: string | null;
  user_online: boolean;
  updated_at: string;
  created_at: string;
  heat_score: number;  // 热度得分
  unread_count: number;  // 未读消息数
  current_ticket_id?: string | null;
  ticket_status?: string | null;
  primary_issue_tag?: string | null;
  current_agent_tag?: string | null;
  risk_level?: string | null;
  review_status?: string | null;
  review_score?: number | null;
  secondary_issue_detected?: boolean;
  last_message?: string | null;
  last_message_at?: string | null;
  last_message_role?: "user" | "assistant" | "human_agent" | "system" | null;
}

export interface SupportStats {
  pending_count: number;  // 等待接入数
  human_count: number;  // 人工服务中数
  total_unread: number;  // 总未读消息数
  high_heat_count: number;  // 高热会话数
}

export interface AgentScoreSnapshot {
  id: string;
  agent_tag: string;
  window_type: string;
  window_start: string;
  window_end: string;
  pass_rate: number | null;
  handoff_rate: number | null;
  avg_review_score: number | null;
  avg_resolution_time_ms: number | null;
  rework_rate: number | null;
  violation_rate: number | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface AgentScoreSnapshotListResponse {
  items: AgentScoreSnapshot[];
  total: number;
  window_type: string;
}

export interface SupportConversationListResponse {
  items: SupportConversation[];
  total: number;
  offset: number;
  limit: number;
}

export interface ConversationStateResponse {
  conversation_id: string;
  conversation_mode: string;
  handoff_state: string;
  handoff_operator: string | null;
  handoff_reason: string | null;
  handoff_at: string | null;
  last_notification_at: string | null;
  current_ticket: TicketSummary | null;
  recent_tasks: RecentTaskSummary[];
  review_summary: ReviewSummary | null;
  latest_review?: ReviewSummary | null;
  secondary_issues: SecondaryIssueSummary[];
  handoff_summary: Record<string, unknown> | null;
  user_online: boolean;
  peer_last_online_at: string | null;
  unread_count: number;
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
  is_delivered?: boolean;
  delivered_at?: string | null;
  read_at?: string | null;
  read_by?: string | null;
  is_withdrawn?: boolean;
  withdrawn_at?: string | null;
  withdrawn_by?: string | null;
  is_edited?: boolean;
  edited_at?: string | null;
  edited_by?: string | null;
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

// 获取最近一批 Agent 绩效快照
export async function getAgentScoreSnapshots(
  windowType = "daily",
  limit = 20
): Promise<AgentScoreSnapshotListResponse> {
  const params = new URLSearchParams();
  params.set("window_type", windowType);
  params.set("limit", String(limit));

  return apiRequest<AgentScoreSnapshotListResponse>(
    `/api/v1/support/agent-score-snapshots?${params.toString()}`
  );
}

// 获取会话状态
export async function getConversationState(
  conversationId: string
): Promise<ConversationStateResponse> {
  return apiRequest<ConversationStateResponse>(
    `/api/v1/support/handoff/${conversationId}`
  );
}

// 获取会话当前主问题单
export async function getActiveSupportTicket(
  conversationId: string
): Promise<TicketDetail> {
  return apiRequest<TicketDetail>(
    `/api/v1/support/conversations/${conversationId}/active-ticket`
  );
}

// 获取会话历史问题单列表
export async function getConversationTickets(
  conversationId: string
): Promise<ConversationTicketsResponse> {
  return apiRequest<ConversationTicketsResponse>(
    `/api/v1/support/conversations/${conversationId}/tickets`
  );
}

// 获取单张问题单详情
export async function getSupportTicketDetail(
  ticketId: string
): Promise<TicketDetail> {
  return apiRequest<TicketDetail>(
    `/api/v1/support/tickets/${ticketId}`
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

// 手动解决问题单
export async function resolveSupportTicket(
  ticketId: string,
  operator: string,
  summary?: string
): Promise<TicketActionResponse> {
  return apiRequest<TicketActionResponse>(
    `/api/v1/support/tickets/${ticketId}/resolve`,
    {
      method: "POST",
      body: JSON.stringify({ operator, summary: summary || "" }),
    }
  );
}

// 手动重开问题单
export async function reopenSupportTicket(
  ticketId: string,
  operator: string,
  reason?: string
): Promise<TicketActionResponse> {
  return apiRequest<TicketActionResponse>(
    `/api/v1/support/tickets/${ticketId}/reopen`,
    {
      method: "POST",
      body: JSON.stringify({ operator, reason: reason || "" }),
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
