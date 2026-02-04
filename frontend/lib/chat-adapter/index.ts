/**
 * Chat Adapter 统一导出
 *
 * 根据 Feature Flag 自动选择新/旧 SDK 实现
 */

import { isNewSDKEnabled, getSDKVersion } from "./config";
import {
  LegacyChatStreamClient,
  LegacyTimelineManager,
  createLegacyUserWebSocketManager,
  createLegacyAgentWebSocketManager,
} from "./legacy-adapter";
import {
  NewChatStreamClient,
  NewTimelineManager,
  createNewUserWebSocketManager,
  createNewAgentWebSocketManager,
} from "./new-adapter";
import type {
  IChatStreamClient,
  ITimelineManager,
  IWebSocketManager,
} from "./types";

// 重新导出类型
export * from "./types";
export * from "./config";

// ==================== 工厂函数 ====================

/**
 * 创建 SSE 流式聊天客户端
 *
 * 根据 Feature Flag 自动选择实现
 */
export function createChatStreamClient(baseUrl: string): IChatStreamClient {
  const version = getSDKVersion();

  if (isNewSDKEnabled()) {
    if (process.env.NODE_ENV === "development") {
      console.log(`[ChatAdapter] Creating SSE client (${version})`);
    }
    return new NewChatStreamClient(baseUrl);
  } else {
    if (process.env.NODE_ENV === "development") {
      console.log(`[ChatAdapter] Creating SSE client (${version})`);
    }
    return new LegacyChatStreamClient();
  }
}

/**
 * 创建 Timeline 管理器
 *
 * 根据 Feature Flag 自动选择实现
 */
export function createTimelineManager(): ITimelineManager {
  const version = getSDKVersion();

  if (isNewSDKEnabled()) {
    if (process.env.NODE_ENV === "development") {
      console.log(`[ChatAdapter] Creating Timeline manager (${version})`);
    }
    return new NewTimelineManager();
  } else {
    if (process.env.NODE_ENV === "development") {
      console.log(`[ChatAdapter] Creating Timeline manager (${version})`);
    }
    return new LegacyTimelineManager();
  }
}

/**
 * 创建用户端 WebSocket 管理器
 *
 * 根据 Feature Flag 自动选择实现
 */
export function createUserWebSocketManager(
  baseUrl: string,
  conversationId: string,
  userId: string
): IWebSocketManager {
  if (isNewSDKEnabled()) {
    return createNewUserWebSocketManager(baseUrl, conversationId, userId);
  } else {
    return createLegacyUserWebSocketManager(baseUrl, conversationId, userId);
  }
}

/**
 * 创建客服端 WebSocket 管理器
 *
 * 根据 Feature Flag 自动选择实现
 */
export function createAgentWebSocketManager(
  baseUrl: string,
  conversationId: string,
  agentId: string
): IWebSocketManager {
  if (isNewSDKEnabled()) {
    return createNewAgentWebSocketManager(baseUrl, conversationId, agentId);
  } else {
    return createLegacyAgentWebSocketManager(baseUrl, conversationId, agentId);
  }
}
