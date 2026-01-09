// 会话相关类型

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  handoff_state?: "ai" | "pending" | "human";
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  products?: string | null;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface CreateConversationRequest {
  user_id: string;
}

export interface PaginatedMessagesResponse {
  messages: Message[];
  next_cursor: string | null;
  has_more: boolean;
}
