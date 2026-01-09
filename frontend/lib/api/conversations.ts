// 会话 API

import type {
  Conversation,
  ConversationWithMessages,
  CreateConversationRequest,
  PaginatedMessagesResponse,
} from "@/types/conversation";
import { apiRequest } from "./client";

export async function getConversations(userId: string): Promise<Conversation[]> {
  return apiRequest<Conversation[]>(
    `/api/v1/conversations?user_id=${encodeURIComponent(userId)}`
  );
}

export async function createConversation(
  request: CreateConversationRequest
): Promise<Conversation> {
  return apiRequest<Conversation>("/api/v1/conversations", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getConversation(
  conversationId: string
): Promise<ConversationWithMessages> {
  return apiRequest<ConversationWithMessages>(
    `/api/v1/conversations/${conversationId}`
  );
}

export async function deleteConversation(
  conversationId: string
): Promise<{ success: boolean }> {
  return apiRequest<{ success: boolean }>(
    `/api/v1/conversations/${conversationId}`,
    {
      method: "DELETE",
    }
  );
}

export async function getConversationMessages(
  conversationId: string,
  options?: { cursor?: string; limit?: number }
): Promise<PaginatedMessagesResponse> {
  const params = new URLSearchParams();
  if (options?.cursor) params.set("cursor", options.cursor);
  if (options?.limit) params.set("limit", String(options.limit));
  
  const query = params.toString();
  const url = `/api/v1/conversations/${conversationId}/messages${query ? `?${query}` : ""}`;
  
  return apiRequest<PaginatedMessagesResponse>(url);
}
