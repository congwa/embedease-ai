/**
 * Timeline Reducer：将 SSE 事件流映射为时间线 item 列表
 *
 * 事件流顺序：
 * 1. meta.start - 流开始
 * 2. [循环] llm.call.start → [reasoning.delta, delta...] → llm.call.end
 *           → tool.start → [products, todos...] → tool.end
 * 3. memory.* - 后处理
 * 4. assistant.final - 流结束
 *
 * 架构设计：
 * - LLMCallCluster：包含 LLM 调用内部的 reasoning/delta 子事件
 * - ToolCallItem：独立的顶层 item，包含工具执行期间的数据事件
 * - 数据事件（products/todos/context_summarized）根据当前上下文归属到 LLMCluster 或 ToolCall
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
  TodosPayload,
  TodoItem,
  FinalPayload,
  ErrorPayload,
  ContextSummarizedPayload,
} from "@/types/chat";
import { isLLMCallInternalEvent } from "@/types/chat";

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

// ==================== LLM 调用内部子事件类型 ====================

/** 推理内容子项（流式文本） */
export interface ReasoningSubItem {
  type: "reasoning";
  id: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

/** 正文内容子项（流式文本） */
export interface ContentSubItem {
  type: "content";
  id: string;
  text: string;
  ts: number;
}

/** 商品列表子项 */
export interface ProductsSubItem {
  type: "products";
  id: string;
  products: Product[];
  ts: number;
}

/** TODO 列表子项 */
export interface TodosSubItem {
  type: "todos";
  id: string;
  todos: TodoItem[];
  ts: number;
}

/** 上下文压缩子项 */
export interface ContextSummarizedSubItem {
  type: "context_summarized";
  id: string;
  messagesBefore: number;
  messagesAfter: number;
  tokensBefore?: number;
  tokensAfter?: number;
  ts: number;
}

/** LLM 调用内部子项联合类型（仅包含真正的 LLM 内部事件） */
export type LLMCallSubItem =
  | ReasoningSubItem
  | ContentSubItem
  | ProductsSubItem
  | TodosSubItem
  | ContextSummarizedSubItem;

// ==================== 工具调用子事件类型 ====================

/** 工具调用内部子项联合类型 */
export type ToolCallSubItem = ProductsSubItem | TodosSubItem | ContextSummarizedSubItem;

// ==================== 时间线顶层 Item 类型 ====================

/** 用户消息 item */
export interface UserMessageItem {
  type: "user.message";
  id: string;
  turnId: string;
  content: string;
  ts: number;
}

/** LLM 调用集群（容器）- 包含 LLM 调用内部的子事件 */
export interface LLMCallClusterItem {
  type: "llm.call.cluster";
  id: string; // llm_call_id
  turnId: string;
  status: ItemStatus;
  messageCount?: number;
  elapsedMs?: number;
  error?: string;
  /** 内部子事件列表（仅 reasoning/content/data 事件） */
  children: LLMCallSubItem[];
  /** 子事件索引：id -> children index */
  childIndexById: Record<string, number>;
  ts: number;
}

/** 工具调用 item（顶层，独立于 LLM 调用） */
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
  input?: unknown;
  /** 工具执行期间的数据事件 */
  children: ToolCallSubItem[];
  childIndexById: Record<string, number>;
  startedAt: number;
  ts: number;
}

/** 错误 item（顶层） */
export interface ErrorItem {
  type: "error";
  id: string;
  turnId: string;
  message: string;
  ts: number;
}

/** 最终完成 item */
export interface FinalItem {
  type: "final";
  id: string;
  turnId: string;
  content?: string;
  ts: number;
}

/** 记忆事件 item */
export interface MemoryEventItem {
  type: "memory.event";
  id: string;
  turnId: string;
  eventType: "extraction.start" | "extraction.complete" | "profile.updated";
  ts: number;
}

/** 客服事件 item */
export interface SupportEventItem {
  type: "support.event";
  id: string;
  turnId: string;
  eventType: "handoff_started" | "handoff_ended" | "human_message" | "connected";
  message?: string;
  ts: number;
}

/** 时间线顶层 item 联合类型 */
export type TimelineItem =
  | UserMessageItem
  | LLMCallClusterItem
  | ToolCallItem
  | ErrorItem
  | FinalItem
  | MemoryEventItem
  | SupportEventItem;

// ==================== 兼容旧组件的类型别名 ====================

/** @deprecated 使用 ReasoningSubItem 代替 */
export interface ReasoningItem {
  type: "assistant.reasoning";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

/** @deprecated 使用 ContentSubItem 代替 */
export interface ContentItem {
  type: "assistant.content";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  ts: number;
}

/** @deprecated 使用 ProductsSubItem 代替 */
export interface ProductsItem {
  type: "assistant.products";
  id: string;
  turnId: string;
  products: Product[];
  ts: number;
}

/** @deprecated 使用 TodosSubItem 代替 */
export interface TodosItem {
  type: "assistant.todos";
  id: string;
  turnId: string;
  todos: TodoItem[];
  ts: number;
}

/** @deprecated 使用 ContextSummarizedSubItem 代替 */
export interface ContextSummarizedItem {
  type: "context.summarized";
  id: string;
  turnId: string;
  messagesBefore: number;
  messagesAfter: number;
  tokensBefore?: number;
  tokensAfter?: number;
  ts: number;
}

/** Timeline state */
export interface TimelineState {
  timeline: TimelineItem[];
  indexById: Record<string, number>; // id -> timeline index
  activeTurn: {
    turnId: string | null;
    currentLlmCallId: string | null; // 当前运行的 LLM 调用 ID
    currentToolCallId: string | null; // 当前运行的工具调用 ID
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
      currentLlmCallId: null,
      currentToolCallId: null,
      isStreaming: false,
    },
  };
}

/** 插入顶层 item 并更新索引 */
function insertItem(state: TimelineState, item: TimelineItem): TimelineState {
  const timeline = [...state.timeline, item];
  const indexById = { ...state.indexById, [item.id]: timeline.length - 1 };
  return { ...state, timeline, indexById };
}

/** 更新顶层 item */
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

/** 获取当前 LLM Call Cluster */
function getCurrentLlmCluster(state: TimelineState): LLMCallClusterItem | undefined {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return undefined;
  const index = state.indexById[llmCallId];
  if (index === undefined) return undefined;
  const item = state.timeline[index];
  if (item.type === "llm.call.cluster") return item;
  return undefined;
}

/** 获取当前 Tool Call Item */
function getCurrentToolCall(state: TimelineState): ToolCallItem | undefined {
  const toolCallId = state.activeTurn.currentToolCallId;
  if (!toolCallId) return undefined;
  const index = state.indexById[toolCallId];
  if (index === undefined) return undefined;
  const item = state.timeline[index];
  if (item.type === "tool.call") return item;
  return undefined;
}

/** 向当前 LLM Cluster 添加子事件 */
function appendSubItemToCurrentCluster(
  state: TimelineState,
  subItem: LLMCallSubItem
): TimelineState {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return state;

  return updateItemById(state, llmCallId, (item) => {
    if (item.type !== "llm.call.cluster") return item;
    const children = [...item.children, subItem];
    const childIndexById = { ...item.childIndexById, [subItem.id]: children.length - 1 };
    return { ...item, children, childIndexById };
  });
}

/** 更新当前 LLM Cluster 中的子事件 */
function updateSubItemInCurrentCluster(
  state: TimelineState,
  subItemId: string,
  updater: (subItem: LLMCallSubItem) => LLMCallSubItem
): TimelineState {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return state;

  return updateItemById(state, llmCallId, (item) => {
    if (item.type !== "llm.call.cluster") return item;
    const subIndex = item.childIndexById[subItemId];
    if (subIndex === undefined) return item;
    const children = [...item.children];
    children[subIndex] = updater(children[subIndex]);
    return { ...item, children };
  });
}

/** 向当前 Tool Call 添加子事件 */
function appendSubItemToCurrentToolCall(
  state: TimelineState,
  subItem: ToolCallSubItem
): TimelineState {
  const toolCallId = state.activeTurn.currentToolCallId;
  if (!toolCallId) return state;

  return updateItemById(state, toolCallId, (item) => {
    if (item.type !== "tool.call") return item;
    const children = [...item.children, subItem];
    const childIndexById = { ...item.childIndexById, [subItem.id]: children.length - 1 };
    return { ...item, children, childIndexById };
  });
}

/** 获取当前 LLM Cluster 中最后一个指定类型的子事件 */
function getLastSubItemOfType<T extends LLMCallSubItem>(
  cluster: LLMCallClusterItem,
  type: T["type"]
): T | undefined {
  for (let i = cluster.children.length - 1; i >= 0; i--) {
    const child = cluster.children[i];
    if (child.type === type) return child as T;
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
      currentLlmCallId: null,
      currentToolCallId: null,
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
    // ==================== 非 LLM 调用内部事件 ====================

    case "meta.start": {
      const payload = event.payload as MetaStartPayload;
      const oldTurnId = turnId;
      const newTurnId = payload.assistant_message_id;

      if (newTurnId && newTurnId !== oldTurnId) {
        const timeline = state.timeline.map((item) =>
          item.turnId === oldTurnId ? { ...item, turnId: newTurnId } : item
        );
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
      const cluster: LLMCallClusterItem = {
        type: "llm.call.cluster",
        id: llmCallId,
        turnId,
        status: "running",
        messageCount: payload.message_count,
        children: [],
        childIndexById: {},
        ts: now,
      };
      const newState = insertItem(state, cluster);
      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentLlmCallId: llmCallId,
          currentToolCallId: null, // 进入 LLM 调用时清除工具上下文
        },
      };
    }

    case "llm.call.end": {
      const payload = event.payload as LlmCallEndPayload;
      const llmCallId = payload.llm_call_id;
      const hasError = !!payload.error;
      const targetId = llmCallId || state.activeTurn.currentLlmCallId;
      if (!targetId) return state;

      const newState = updateItemById(state, targetId, (item) => {
        if (item.type !== "llm.call.cluster") return item;
        return {
          ...item,
          status: hasError ? "error" : "success",
          elapsedMs: payload.elapsed_ms,
          error: payload.error,
        };
      });

      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentLlmCallId: null, // LLM 调用结束
        },
      };
    }

    case "assistant.final": {
      const payload = event.payload as FinalPayload;

      // 关闭所有 LLM Cluster 中的 open reasoning
      let newState = state;
      for (const item of state.timeline) {
        if (item.type === "llm.call.cluster" && item.turnId === turnId) {
          newState = updateItemById(newState, item.id, (cluster) => {
            if (cluster.type !== "llm.call.cluster") return cluster;
            const children = cluster.children.map((child) =>
              child.type === "reasoning" && child.isOpen
                ? { ...child, isOpen: false }
                : child
            );
            return { ...cluster, children };
          });
        }
      }

      // 插入 FinalItem
      const finalItem: FinalItem = {
        type: "final",
        id: `final:${event.seq}`,
        turnId,
        content: payload.content,
        ts: now,
      };
      newState = insertItem(newState, finalItem);

      return {
        ...newState,
        activeTurn: { ...newState.activeTurn, isStreaming: false },
      };
    }

    case "memory.extraction.start":
    case "memory.extraction.complete":
    case "memory.profile.updated": {
      const eventType = event.type.replace("memory.", "") as MemoryEventItem["eventType"];
      const item: MemoryEventItem = {
        type: "memory.event",
        id: `memory:${event.seq}`,
        turnId,
        eventType,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "support.handoff_started":
    case "support.handoff_ended":
    case "support.human_message":
    case "support.connected": {
      const eventType = event.type.replace("support.", "") as SupportEventItem["eventType"];
      const payload = event.payload as { message?: string };
      const item: SupportEventItem = {
        type: "support.event",
        id: `support:${event.seq}`,
        turnId,
        eventType,
        message: payload?.message,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "support.ping":
      // 心跳事件不渲染
      return state;

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

    // ==================== LLM 调用内部事件（存入 Cluster） ====================

    case "assistant.reasoning.delta": {
      const payload = event.payload as TextDeltaPayload;
      const delta = payload.delta;
      if (!delta) return state;

      const cluster = getCurrentLlmCluster(state);
      if (!cluster) return state;

      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(cluster, "reasoning");
      if (lastReasoning) {
        return updateSubItemInCurrentCluster(state, lastReasoning.id, (sub) => {
          if (sub.type !== "reasoning") return sub;
          return { ...sub, text: sub.text + delta };
        });
      }

      const subItem: ReasoningSubItem = {
        type: "reasoning",
        id: crypto.randomUUID(),
        text: delta,
        isOpen: true,
        ts: now,
      };
      return appendSubItemToCurrentCluster(state, subItem);
    }

    case "assistant.delta": {
      const payload = event.payload as TextDeltaPayload;
      const delta = payload.delta;
      if (!delta) return state;

      const cluster = getCurrentLlmCluster(state);
      if (!cluster) return state;

      // 关闭上一个 open 的 reasoning
      let newState = state;
      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(cluster, "reasoning");
      if (lastReasoning && lastReasoning.isOpen) {
        newState = updateSubItemInCurrentCluster(newState, lastReasoning.id, (sub) => {
          if (sub.type !== "reasoning") return sub;
          return { ...sub, isOpen: false };
        });
      }

      // 追加到现有 content 或创建新的
      const updatedCluster = getCurrentLlmCluster(newState);
      if (!updatedCluster) return newState;
      const lastContent = getLastSubItemOfType<ContentSubItem>(updatedCluster, "content");
      if (lastContent) {
        return updateSubItemInCurrentCluster(newState, lastContent.id, (sub) => {
          if (sub.type !== "content") return sub;
          return { ...sub, text: sub.text + delta };
        });
      }

      const subItem: ContentSubItem = {
        type: "content",
        id: crypto.randomUUID(),
        text: delta,
        ts: now,
      };
      return appendSubItemToCurrentCluster(newState, subItem);
    }

    // ==================== 工具调用事件（顶层 item，在 llm.call.end 之后） ====================

    case "tool.start": {
      const payload = event.payload as ToolStartPayload;
      const toolCallId = payload.tool_call_id || crypto.randomUUID();
      const toolItem: ToolCallItem = {
        type: "tool.call",
        id: toolCallId,
        turnId,
        name: payload.name,
        label: getToolLabel(payload.name),
        status: "running",
        input: payload.input,
        children: [],
        childIndexById: {},
        startedAt: now,
        ts: now,
      };
      const newState = insertItem(state, toolItem);
      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentToolCallId: toolCallId,
        },
      };
    }

    case "tool.end": {
      const payload = event.payload as ToolEndPayload;
      const toolCallId = payload.tool_call_id || state.activeTurn.currentToolCallId;
      if (!toolCallId) return state;

      const newState = updateItemById(state, toolCallId, (item) => {
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

      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentToolCallId: null, // 工具调用结束
        },
      };
    }

    // ==================== 数据事件（根据上下文归属到 LLMCluster 或 ToolCall） ====================

    case "assistant.products": {
      const payload = event.payload as ProductsPayload;
      const products = payload.items;
      if (!products || products.length === 0) return state;

      const subItem: ProductsSubItem = {
        type: "products",
        id: `products:${event.seq}`,
        products,
        ts: now,
      };

      // 优先归属到当前工具调用，否则归属到 LLM 调用
      if (state.activeTurn.currentToolCallId) {
        return appendSubItemToCurrentToolCall(state, subItem);
      }
      return appendSubItemToCurrentCluster(state, subItem);
    }

    case "assistant.todos": {
      const payload = event.payload as TodosPayload;
      const todos = payload.todos;
      if (!todos || todos.length === 0) return state;

      const subItem: TodosSubItem = {
        type: "todos",
        id: `todos:${event.seq}`,
        todos,
        ts: now,
      };

      if (state.activeTurn.currentToolCallId) {
        return appendSubItemToCurrentToolCall(state, subItem);
      }
      return appendSubItemToCurrentCluster(state, subItem);
    }

    case "context.summarized": {
      const payload = event.payload as ContextSummarizedPayload;
      const subItem: ContextSummarizedSubItem = {
        type: "context_summarized",
        id: `context-summarized:${event.seq}`,
        messagesBefore: payload.messages_before,
        messagesAfter: payload.messages_after,
        tokensBefore: payload.tokens_before,
        tokensAfter: payload.tokens_after,
        ts: now,
      };

      if (state.activeTurn.currentToolCallId) {
        return appendSubItemToCurrentToolCall(state, subItem);
      }
      return appendSubItemToCurrentCluster(state, subItem);
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
      currentLlmCallId: null,
      currentToolCallId: null,
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
      // assistant 消息：创建一个虚拟的 LLMCallCluster 来包含历史内容
      const children: LLMCallSubItem[] = [];
      const childIndexById: Record<string, number> = {};

      // 添加 content 子项
      const contentId = `${msg.id}-content`;
      const contentSubItem: ContentSubItem = {
        type: "content",
        id: contentId,
        text: msg.content,
        ts: Date.now(),
      };
      childIndexById[contentId] = children.length;
      children.push(contentSubItem);

      // 如果有 products，添加 products 子项
      if (msg.products && msg.products.length > 0) {
        const productsId = `${msg.id}-products`;
        const productsSubItem: ProductsSubItem = {
          type: "products",
          id: productsId,
          products: msg.products,
          ts: Date.now(),
        };
        childIndexById[productsId] = children.length;
        children.push(productsSubItem);
      }

      // 创建 LLMCallCluster
      const cluster: LLMCallClusterItem = {
        type: "llm.call.cluster",
        id: msg.id,
        turnId: msg.id,
        status: "success",
        children,
        childIndexById,
        ts: Date.now(),
      };
      state = insertItem(state, cluster);
    }
  }

  return state;
}
