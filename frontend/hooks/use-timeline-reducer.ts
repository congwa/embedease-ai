/**
 * Timeline Reducer：将 SSE 事件流映射为时间线 item 列表
 *
 * 设计原则：
 * - 每种 SSE 事件类型对应一种或多种 TimelineItem
 * - start 事件插入新 item，end 事件更新同一个 item
 * - 支持按 id 快速定位更新（O(1)）
 * - 推理/正文增量归属到当前运行的 LLM 调用
 */

import type { Product } from "@/types/product";
import type {
  ChatEvent,
  MetaStartPayload,
  LlmCallStartPayload,
  LlmCallEndPayload,
  TextDeltaPayload,
  ToolStartPayload,
  ToolEndPayload,
  ProductsPayload,
  FinalPayload,
  ErrorPayload,
} from "@/types/chat";

/** 工具名称中文映射 */
const TOOL_LABEL_MAP: Record<string, string> = {
  search_products: "商品搜索",
  get_product_details: "商品详情",
  filter_by_price: "价格筛选",
  compare_products: "商品对比",
  guide_user: "用户引导",
};

export function getToolLabel(name: string): string {
  return TOOL_LABEL_MAP[name] || name.slice(0, 10);
}

/** 状态类型 */
export type ItemStatus = "running" | "success" | "error" | "empty";

/** 用户消息 item */
export interface UserMessageItem {
  type: "user.message";
  id: string;
  turnId: string;
  content: string;
  ts: number;
}

/** LLM 调用状态 item */
export interface LlmCallItem {
  type: "llm.call";
  id: string; // llm_call_id
  turnId: string;
  status: ItemStatus;
  messageCount?: number;
  elapsedMs?: number;
  error?: string;
  ts: number;
}

/** 推理内容 item（流式文本） */
export interface ReasoningItem {
  type: "assistant.reasoning";
  id: string;
  turnId: string;
  llmCallId?: string; // 归属的 LLM 调用
  text: string;
  isOpen: boolean;
  ts: number;
}

/** 正文内容 item（流式文本） */
export interface ContentItem {
  type: "assistant.content";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  ts: number;
}

/** 工具调用状态 item */
export interface ToolCallItem {
  type: "tool.call";
  id: string; // tool_call_id
  turnId: string;
  name: string;
  label: string;
  status: ItemStatus;
  count?: number;
  elapsedMs?: number;
  error?: string;
  startedAt: number;
  ts: number;
}

/** 商品列表 item */
export interface ProductsItem {
  type: "assistant.products";
  id: string;
  turnId: string;
  products: Product[];
  ts: number;
}

/** 错误 item */
export interface ErrorItem {
  type: "error";
  id: string;
  turnId: string;
  message: string;
  ts: number;
}

/** 时间线 item 联合类型 */
export type TimelineItem =
  | UserMessageItem
  | LlmCallItem
  | ReasoningItem
  | ContentItem
  | ToolCallItem
  | ProductsItem
  | ErrorItem;

/** Timeline state */
export interface TimelineState {
  timeline: TimelineItem[];
  indexById: Record<string, number>; // id -> timeline index
  activeTurn: {
    turnId: string | null;
    llmStack: string[]; // 当前运行的 llm_call_id 栈
    isStreaming: boolean;
  };
}

/** 初始状态 */
export function createInitialState(): TimelineState {
  return {
    timeline: [],
    indexById: {},
    activeTurn: {
      turnId: null,
      llmStack: [],
      isStreaming: false,
    },
  };
}

/** 插入 item 并更新索引 */
function insertItem(state: TimelineState, item: TimelineItem): TimelineState {
  const timeline = [...state.timeline, item];
  const indexById = { ...state.indexById, [item.id]: timeline.length - 1 };
  return { ...state, timeline, indexById };
}

/** 更新 item */
function updateItemById(
  state: TimelineState,
  id: string,
  updater: (item: TimelineItem) => TimelineItem
): TimelineState {
  const index = state.indexById[id];
  if (index === undefined) return state;

  const timeline = [...state.timeline];
  timeline[index] = updater(timeline[index]);
  return { ...state, timeline };
}

/** 获取当前运行的 LLM call ID */
function getCurrentLlmCallId(state: TimelineState): string | undefined {
  const stack = state.activeTurn.llmStack;
  return stack.length > 0 ? stack[stack.length - 1] : undefined;
}

/** 获取最后一个同类型 item */
function getLastItemOfType<T extends TimelineItem>(
  state: TimelineState,
  type: T["type"],
  turnId: string
): T | undefined {
  for (let i = state.timeline.length - 1; i >= 0; i--) {
    const item = state.timeline[i];
    if (item.type === type && item.turnId === turnId) {
      return item as T;
    }
  }
  return undefined;
}

/** 添加用户消息 */
export function addUserMessage(
  state: TimelineState,
  id: string,
  content: string
): TimelineState {
  const item: UserMessageItem = {
    type: "user.message",
    id,
    turnId: id, // 用户消息的 turnId 就是自己
    content,
    ts: Date.now(),
  };
  return insertItem(state, item);
}

/** 开始新的 assistant turn */
export function startAssistantTurn(
  state: TimelineState,
  turnId: string
): TimelineState {
  return {
    ...state,
    activeTurn: {
      turnId,
      llmStack: [],
      isStreaming: true,
    },
  };
}

/** Reducer：处理 SSE 事件 */
export function timelineReducer(
  state: TimelineState,
  event: ChatEvent
): TimelineState {
  const turnId = state.activeTurn.turnId;
  if (!turnId) return state;

  const now = Date.now();

  switch (event.type) {
    case "meta.start": {
      const payload = event.payload as MetaStartPayload;
      const oldTurnId = turnId;
      const newTurnId = payload.assistant_message_id;

      if (newTurnId && newTurnId !== oldTurnId) {
        // 更新所有属于旧 turnId 的 items
        const timeline = state.timeline.map((item) =>
          item.turnId === oldTurnId ? { ...item, turnId: newTurnId } : item
        );
        // 重建索引
        const indexById: Record<string, number> = {};
        timeline.forEach((item, i) => {
          indexById[item.id] = i;
        });
        return {
          ...state,
          timeline,
          indexById,
          activeTurn: { ...state.activeTurn, turnId: newTurnId },
        };
      }
      return state;
    }

    case "llm.call.start": {
      const payload = event.payload as LlmCallStartPayload;
      const llmCallId = payload.llm_call_id || crypto.randomUUID();
      const item: LlmCallItem = {
        type: "llm.call",
        id: llmCallId,
        turnId,
        status: "running",
        messageCount: payload.message_count,
        ts: now,
      };
      const newState = insertItem(state, item);
      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          llmStack: [...newState.activeTurn.llmStack, llmCallId],
        },
      };
    }

    case "llm.call.end": {
      const payload = event.payload as LlmCallEndPayload;
      const llmCallId = payload.llm_call_id;
      const hasError = !!payload.error;

      // 如果有 llm_call_id，用它定位；否则用栈顶
      const targetId = llmCallId || getCurrentLlmCallId(state);
      if (!targetId) return state;

      const newState = updateItemById(state, targetId, (item) => {
        if (item.type !== "llm.call") return item;
        return {
          ...item,
          status: hasError ? "error" : "success",
          elapsedMs: payload.elapsed_ms,
          error: payload.error,
        };
      });

      // 从栈中移除
      const llmStack = newState.activeTurn.llmStack.filter(
        (id) => id !== targetId
      );
      return {
        ...newState,
        activeTurn: { ...newState.activeTurn, llmStack },
      };
    }

    case "assistant.reasoning.delta": {
      const payload = event.payload as TextDeltaPayload;
      const delta = payload.delta;
      if (!delta) return state;

      const currentLlmId = getCurrentLlmCallId(state);
      const lastReasoning = getLastItemOfType<ReasoningItem>(
        state,
        "assistant.reasoning",
        turnId
      );

      // 如果最后一个 reasoning item 属于同一个 LLM call，追加
      if (lastReasoning && lastReasoning.llmCallId === currentLlmId) {
        return updateItemById(state, lastReasoning.id, (item) => {
          if (item.type !== "assistant.reasoning") return item;
          return { ...item, text: item.text + delta };
        });
      }

      // 否则创建新的 reasoning item
      const item: ReasoningItem = {
        type: "assistant.reasoning",
        id: crypto.randomUUID(),
        turnId,
        llmCallId: currentLlmId,
        text: delta,
        isOpen: true,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "assistant.delta": {
      const payload = event.payload as TextDeltaPayload;
      const delta = payload.delta;
      if (!delta) return state;

      const currentLlmId = getCurrentLlmCallId(state);
      const lastContent = getLastItemOfType<ContentItem>(
        state,
        "assistant.content",
        turnId
      );

      // 追加到同一个 content item
      if (lastContent && lastContent.llmCallId === currentLlmId) {
        return updateItemById(state, lastContent.id, (item) => {
          if (item.type !== "assistant.content") return item;
          return { ...item, text: item.text + delta };
        });
      }

      // 创建新的 content item
      const item: ContentItem = {
        type: "assistant.content",
        id: crypto.randomUUID(),
        turnId,
        llmCallId: currentLlmId,
        text: delta,
        ts: now,
      };

      // 如果有上一个 reasoning item 且是 open 的，关闭它
      let newState = state;
      const lastReasoning = getLastItemOfType<ReasoningItem>(
        state,
        "assistant.reasoning",
        turnId
      );
      if (lastReasoning && lastReasoning.isOpen) {
        newState = updateItemById(state, lastReasoning.id, (item) => {
          if (item.type !== "assistant.reasoning") return item;
          return { ...item, isOpen: false };
        });
      }

      return insertItem(newState, item);
    }

    case "tool.start": {
      const payload = event.payload as ToolStartPayload;
      const toolCallId = payload.tool_call_id || crypto.randomUUID();
      const item: ToolCallItem = {
        type: "tool.call",
        id: toolCallId,
        turnId,
        name: payload.name,
        label: getToolLabel(payload.name),
        status: "running",
        startedAt: now,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "tool.end": {
      const payload = event.payload as ToolEndPayload;
      const toolCallId = payload.tool_call_id;
      if (!toolCallId) return state;

      return updateItemById(state, toolCallId, (item) => {
        if (item.type !== "tool.call") return item;
        const elapsedMs = Date.now() - item.startedAt;
        return {
          ...item,
          status: payload.status || (payload.error ? "error" : "success"),
          count: payload.count,
          elapsedMs,
          error: payload.error,
        };
      });
    }

    case "assistant.products": {
      const payload = event.payload as ProductsPayload;
      const products = payload.items;
      if (!products || products.length === 0) return state;

      const item: ProductsItem = {
        type: "assistant.products",
        id: `products:${event.seq}`,
        turnId,
        products,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "assistant.final": {
      const payload = event.payload as FinalPayload;

      // 关闭所有 open 的 reasoning
      let newState = state;
      state.timeline.forEach((item) => {
        if (
          item.type === "assistant.reasoning" &&
          item.turnId === turnId &&
          item.isOpen
        ) {
          newState = updateItemById(newState, item.id, (it) => {
            if (it.type !== "assistant.reasoning") return it;
            return { ...it, isOpen: false };
          });
        }
      });

      // 如果 final 的 content 比我们累积的更长，补齐
      const lastContent = getLastItemOfType<ContentItem>(
        newState,
        "assistant.content",
        turnId
      );
      if (payload.content && lastContent) {
        const accumulated = lastContent.text;
        if (
          payload.content.startsWith(accumulated) &&
          payload.content.length > accumulated.length
        ) {
          const rest = payload.content.slice(accumulated.length);
          newState = updateItemById(newState, lastContent.id, (item) => {
            if (item.type !== "assistant.content") return item;
            return { ...item, text: item.text + rest };
          });
        }
      }

      // 标记 streaming 结束
      return {
        ...newState,
        activeTurn: { ...newState.activeTurn, isStreaming: false },
      };
    }

    case "error": {
      const payload = event.payload as ErrorPayload;
      const item: ErrorItem = {
        type: "error",
        id: `error:${event.seq}`,
        turnId,
        message: payload.message || "未知错误",
        ts: now,
      };
      return insertItem(state, item);
    }

    default:
      return state;
  }
}

/** 清除指定 turn 的所有 items（用于中断） */
export function clearTurn(state: TimelineState, turnId: string): TimelineState {
  const timeline = state.timeline.filter((item) => item.turnId !== turnId);
  const indexById: Record<string, number> = {};
  timeline.forEach((item, i) => {
    indexById[item.id] = i;
  });
  return {
    ...state,
    timeline,
    indexById,
    activeTurn: {
      turnId: null,
      llmStack: [],
      isStreaming: false,
    },
  };
}

/** 结束当前 turn */
export function endTurn(state: TimelineState): TimelineState {
  return {
    ...state,
    activeTurn: {
      ...state.activeTurn,
      isStreaming: false,
    },
  };
}

/** 从历史消息转换为 timeline */
export function historyToTimeline(
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    products?: Product[];
  }>
): TimelineState {
  let state = createInitialState();

  for (const msg of messages) {
    if (msg.role === "user") {
      state = addUserMessage(state, msg.id, msg.content);
    } else {
      // assistant 消息：创建 content item
      const contentItem: ContentItem = {
        type: "assistant.content",
        id: `${msg.id}-content`,
        turnId: msg.id,
        text: msg.content,
        ts: Date.now(),
      };
      state = insertItem(state, contentItem);

      // 如果有 products
      if (msg.products && msg.products.length > 0) {
        const productsItem: ProductsItem = {
          type: "assistant.products",
          id: `${msg.id}-products`,
          turnId: msg.id,
          products: msg.products,
          ts: Date.now(),
        };
        state = insertItem(state, productsItem);
      }
    }
  }

  return state;
}
