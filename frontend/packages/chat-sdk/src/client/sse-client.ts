/**
 * SSE 流式聊天客户端
 */

import type { ChatEvent } from "../core/events";
import type { ChatRequest } from "../core/types";
import type { TimelineState } from "../timeline/types";
import {
  createInitialState,
  timelineReducer,
  addUserMessage,
  startAssistantTurn,
  endTurn,
} from "../timeline";

export interface StreamChatController {
  abort: () => void;
}

export interface StreamChatOptions {
  /** 请求中止控制器 */
  controller?: StreamChatController;
  /** 自定义请求头 */
  headers?: Record<string, string>;
  /** 请求超时（毫秒） */
  timeout?: number;
}

/**
 * SSE 流式聊天函数
 *
 * @param baseUrl API 基础 URL
 * @param request 聊天请求
 * @param options 可选配置
 * @returns AsyncGenerator<ChatEvent>
 */
export async function* streamChat(
  baseUrl: string,
  request: ChatRequest,
  options?: StreamChatOptions
): AsyncGenerator<ChatEvent, void, unknown> {
  const abortController = new AbortController();

  if (options?.controller) {
    options.controller.abort = () => {
      abortController.abort();
    };
  }

  const response = await fetch(`${baseUrl}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    body: JSON.stringify(request),
    signal: abortController.signal,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("无法读取响应流");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data) {
            try {
              const event = JSON.parse(data) as ChatEvent;
              yield event;
            } catch {
              // 忽略单条损坏事件
            }
          }
        }
      }
    }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return;
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}

/**
 * streamWithTimeline 返回类型
 */
export interface StreamWithTimelineResult {
  /** 事件生成器 */
  events: AsyncGenerator<ChatEvent, void, unknown>;
  /** 获取当前 Timeline 状态 */
  getTimeline: () => TimelineState;
  /** 中止流 */
  abort: () => void;
}

/**
 * ChatClient 类
 *
 * 封装 SSE 流式聊天功能
 */
export class ChatClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private controller: StreamChatController = { abort: () => {} };

  constructor(config: { baseUrl: string; headers?: Record<string, string> }) {
    this.baseUrl = config.baseUrl;
    this.headers = config.headers || {};
  }

  /**
   * 发送消息并获取流式响应
   */
  async *stream(
    request: ChatRequest
  ): AsyncGenerator<ChatEvent, void, unknown> {
    this.controller = { abort: () => {} };
    yield* streamChat(this.baseUrl, request, {
      controller: this.controller,
      headers: this.headers,
    });
  }

  /**
   * 发送消息并获取流式响应（带 Timeline 状态管理）
   *
   * @param request 聊天请求
   * @param options 可选配置
   * @returns StreamWithTimelineResult
   */
  streamWithTimeline(
    request: ChatRequest,
    options?: {
      initialState?: TimelineState;
      userMessageId?: string;
      assistantTurnId?: string;
    }
  ): StreamWithTimelineResult {
    let state = options?.initialState ?? createInitialState();
    const userMessageId = options?.userMessageId ?? crypto.randomUUID();
    const assistantTurnId = options?.assistantTurnId ?? crypto.randomUUID();

    // 添加用户消息并开始助手 Turn
    state = addUserMessage(state, userMessageId, request.message, request.images);
    state = startAssistantTurn(state, assistantTurnId);

    this.controller = { abort: () => {} };

    const self = this;

    async function* eventGenerator(): AsyncGenerator<ChatEvent, void, unknown> {
      try {
        for await (const event of streamChat(self.baseUrl, request, {
          controller: self.controller,
          headers: self.headers,
        })) {
          state = timelineReducer(state, event);
          yield event;
        }
        state = endTurn(state);
      } catch (error) {
        if (error instanceof Error && error.name !== "AbortError") {
          throw error;
        }
      }
    }

    return {
      events: eventGenerator(),
      getTimeline: () => state,
      abort: () => this.controller.abort(),
    };
  }

  /**
   * 中止当前流
   */
  abort(): void {
    this.controller.abort();
  }
}
