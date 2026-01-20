/**
 * Timeline 状态工具函数（纯函数，无副作用）
 *
 * 从 use-timeline-reducer.ts 提取的核心逻辑，供 Zustand Store 使用
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
  ImageAttachment,
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

// ==================== LLM 调用内部子事件类型 ====================

export interface ReasoningSubItem {
  type: "reasoning";
  id: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

export interface ContentSubItem {
  type: "content";
  id: string;
  text: string;
  ts: number;
}

export interface ProductsSubItem {
  type: "products";
  id: string;
  products: Product[];
  ts: number;
}

export interface TodosSubItem {
  type: "todos";
  id: string;
  todos: TodoItem[];
  ts: number;
}

export interface ContextSummarizedSubItem {
  type: "context_summarized";
  id: string;
  messagesBefore: number;
  messagesAfter: number;
  tokensBefore?: number;
  tokensAfter?: number;
  ts: number;
}

export type LLMCallSubItem =
  | ReasoningSubItem
  | ContentSubItem
  | ProductsSubItem
  | TodosSubItem
  | ContextSummarizedSubItem;

export type ToolCallSubItem = ProductsSubItem | TodosSubItem | ContextSummarizedSubItem;

// ==================== 时间线顶层 Item 类型 ====================

export interface UserMessageItem {
  type: "user.message";
  id: string;
  turnId: string;
  content: string;
  images?: ImageAttachment[];
  ts: number;
  // 撤回/编辑相关
  isWithdrawn?: boolean;
  withdrawnAt?: string;
  withdrawnBy?: string;
  isEdited?: boolean;
  editedAt?: string;
  editedBy?: string;
}

export interface LLMCallClusterItem {
  type: "llm.call.cluster";
  id: string;
  turnId: string;
  status: ItemStatus;
  messageCount?: number;
  elapsedMs?: number;
  error?: string;
  children: LLMCallSubItem[];
  childIndexById: Record<string, number>;
  ts: number;
}

export interface ToolCallItem {
  type: "tool.call";
  id: string;
  turnId: string;
  name: string;
  label: string;
  status: ItemStatus;
  count?: number;
  elapsedMs?: number;
  error?: string;
  input?: unknown;
  children: ToolCallSubItem[];
  childIndexById: Record<string, number>;
  startedAt: number;
  ts: number;
}

export interface ErrorItem {
  type: "error";
  id: string;
  turnId: string;
  message: string;
  ts: number;
}

export interface FinalItem {
  type: "final";
  id: string;
  turnId: string;
  content?: string;
  ts: number;
}

export interface MemoryEventItem {
  type: "memory.event";
  id: string;
  turnId: string;
  eventType: "extraction.start" | "extraction.complete" | "profile.updated";
  ts: number;
}

export interface SupportEventItem {
  type: "support.event";
  id: string;
  turnId: string;
  eventType: "handoff_started" | "handoff_ended" | "human_message" | "connected" | "human_mode";
  message?: string;
  content?: string;
  operator?: string;
  messageId?: string;
  ts: number;
}

export interface GreetingItem {
  type: "greeting";
  id: string;
  turnId: string;
  title?: string;
  subtitle?: string;
  body: string;
  cta?: {
    text: string;
    payload: string;
  };
  delayMs: number;
  channel: string;
  ts: number;
}

export interface WaitingItem {
  type: "waiting";
  id: string;
  turnId: string;
  ts: number;
}

export type TimelineItem =
  | UserMessageItem
  | LLMCallClusterItem
  | ToolCallItem
  | ErrorItem
  | FinalItem
  | MemoryEventItem
  | SupportEventItem
  | GreetingItem
  | WaitingItem;

export interface TimelineState {
  timeline: TimelineItem[];
  indexById: Record<string, number>;
  activeTurn: {
    turnId: string | null;
    currentLlmCallId: string | null;
    currentToolCallId: string | null;
    isStreaming: boolean;
  };
}

// ==================== 状态操作函数 ====================

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

function insertItem(state: TimelineState, item: TimelineItem): TimelineState {
  const timeline = [...state.timeline, item];
  const indexById = { ...state.indexById, [item.id]: timeline.length - 1 };
  return { ...state, timeline, indexById };
}

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

function getCurrentLlmCluster(state: TimelineState): LLMCallClusterItem | undefined {
  const llmCallId = state.activeTurn.currentLlmCallId;
  if (!llmCallId) return undefined;
  const index = state.indexById[llmCallId];
  if (index === undefined) return undefined;
  const item = state.timeline[index];
  if (item.type === "llm.call.cluster") return item;
  return undefined;
}

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

export function addUserMessage(
  state: TimelineState,
  id: string,
  content: string,
  images?: ImageAttachment[]
): TimelineState {
  const item: UserMessageItem = {
    type: "user.message",
    id,
    turnId: id,
    content,
    images,
    ts: Date.now(),
  };
  return insertItem(state, item);
}

export function addGreetingMessage(
  state: TimelineState,
  greeting: {
    id: string;
    title?: string;
    subtitle?: string;
    body: string;
    cta?: { text: string; payload: string };
    delayMs?: number;
    channel?: string;
  }
): TimelineState {
  const item: GreetingItem = {
    type: "greeting",
    id: greeting.id,
    turnId: greeting.id,
    title: greeting.title,
    subtitle: greeting.subtitle,
    body: greeting.body,
    cta: greeting.cta,
    delayMs: greeting.delayMs || 0,
    channel: greeting.channel || "web",
    ts: Date.now(),
  };
  return insertItem(state, item);
}

export function startAssistantTurn(state: TimelineState, turnId: string): TimelineState {
  // 插入等待项，显示加载状态
  const waitingItem: WaitingItem = {
    type: "waiting",
    id: `waiting-${turnId}`,
    turnId,
    ts: Date.now(),
  };
  const newState = insertItem(state, waitingItem);
  
  return {
    ...newState,
    activeTurn: {
      turnId,
      currentLlmCallId: null,
      currentToolCallId: null,
      isStreaming: true,
    },
  };
}

function removeWaitingItem(state: TimelineState, turnId: string): TimelineState {
  const waitingId = `waiting-${turnId}`;
  const index = state.indexById[waitingId];
  if (index === undefined) return state;
  
  const timeline = state.timeline.filter((_, i) => i !== index);
  const indexById: Record<string, number> = {};
  timeline.forEach((item, i) => {
    indexById[item.id] = i;
  });
  return { ...state, timeline, indexById };
}

export function timelineReducer(state: TimelineState, event: ChatEvent): TimelineState {
  const turnId = state.activeTurn.turnId;
  if (!turnId) return state;

  const now = Date.now();

  switch (event.type) {
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
      // 移除等待项
      const stateWithoutWaiting = removeWaitingItem(state, turnId);
      
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
      const newState = insertItem(stateWithoutWaiting, cluster);
      return {
        ...newState,
        activeTurn: {
          ...newState.activeTurn,
          currentLlmCallId: llmCallId,
          currentToolCallId: null,
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
          currentLlmCallId: null,
        },
      };
    }

    case "assistant.final": {
      const payload = event.payload as FinalPayload;

      let newState = state;
      for (const item of state.timeline) {
        if (item.type === "llm.call.cluster" && item.turnId === turnId) {
          newState = updateItemById(newState, item.id, (cluster) => {
            if (cluster.type !== "llm.call.cluster") return cluster;
            const children = cluster.children.map((child) =>
              child.type === "reasoning" && child.isOpen ? { ...child, isOpen: false } : child
            );
            return { ...cluster, children };
          });
        }
      }

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
    case "support.human_mode":
    case "support.connected": {
      const eventType = event.type.replace("support.", "") as SupportEventItem["eventType"];
      const payload = event.payload as {
        message?: string;
        content?: string;
        operator?: string;
        message_id?: string;
      };
      const item: SupportEventItem = {
        type: "support.event",
        id: `support:${event.seq || crypto.randomUUID()}`,
        turnId,
        eventType,
        message: payload?.message,
        content: payload?.content,
        operator: payload?.operator,
        messageId: payload?.message_id,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "support.ping":
      return state;

    case "support.message_withdrawn": {
      const payload = event.payload as {
        message_id: string;
        withdrawn_by: string;
        withdrawn_at: string;
      };
      // 更新对应消息的撤回状态
      const msgIndex = state.indexById[payload.message_id];
      if (msgIndex !== undefined) {
        const timeline = [...state.timeline];
        const item = timeline[msgIndex];
        if (item.type === "user.message") {
          timeline[msgIndex] = {
            ...item,
            isWithdrawn: true,
            withdrawnAt: payload.withdrawn_at,
            withdrawnBy: payload.withdrawn_by,
          };
          return { ...state, timeline };
        }
      }
      return state;
    }

    case "support.message_edited": {
      const payload = event.payload as {
        message_id: string;
        new_content: string;
        edited_by: string;
        edited_at: string;
        deleted_message_ids?: string[];
      };
      // 更新对应消息的内容和编辑状态
      let newState = state;
      const msgIndex = state.indexById[payload.message_id];
      if (msgIndex !== undefined) {
        const timeline = [...newState.timeline];
        const item = timeline[msgIndex];
        if (item.type === "user.message") {
          timeline[msgIndex] = {
            ...item,
            content: payload.new_content,
            isEdited: true,
            editedAt: payload.edited_at,
            editedBy: payload.edited_by,
          };
          newState = { ...newState, timeline };
        }
      }
      // 删除后续被删除的消息
      if (payload.deleted_message_ids && payload.deleted_message_ids.length > 0) {
        const deletedSet = new Set(payload.deleted_message_ids);
        const timeline = newState.timeline.filter((item) => !deletedSet.has(item.id));
        const indexById: Record<string, number> = {};
        timeline.forEach((item, i) => {
          indexById[item.id] = i;
        });
        newState = { ...newState, timeline, indexById };
      }
      return newState;
    }

    case "support.messages_deleted": {
      const payload = event.payload as {
        message_ids: string[];
      };
      if (!payload.message_ids || payload.message_ids.length === 0) return state;
      const deletedSet = new Set(payload.message_ids);
      const timeline = state.timeline.filter((item) => !deletedSet.has(item.id));
      const indexById: Record<string, number> = {};
      timeline.forEach((item, i) => {
        indexById[item.id] = i;
      });
      return { ...state, timeline, indexById };
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

      let newState = state;
      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(cluster, "reasoning");
      if (lastReasoning && lastReasoning.isOpen) {
        newState = updateSubItemInCurrentCluster(newState, lastReasoning.id, (sub) => {
          if (sub.type !== "reasoning") return sub;
          return { ...sub, isOpen: false };
        });
      }

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
          currentToolCallId: null,
        },
      };
    }

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

export function endTurn(state: TimelineState): TimelineState {
  return {
    ...state,
    activeTurn: {
      ...state.activeTurn,
      isStreaming: false,
    },
  };
}

export function historyToTimeline(
  messages: Array<{
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    products?: Product[];
    message_type?: string;
    extra_metadata?: {
      greeting_config?: {
        title?: string;
        subtitle?: string;
        body?: string;
      };
      cta?: { text: string; payload: string };
      delay_ms?: number;
      channel?: string;
    };
  }>
): TimelineState {
  let state = createInitialState();

  for (const msg of messages) {
    if (msg.role === "user") {
      state = addUserMessage(state, msg.id, msg.content);
    } else if (msg.role === "system" && msg.message_type === "greeting") {
      const meta = msg.extra_metadata;
      state = addGreetingMessage(state, {
        id: msg.id,
        title: meta?.greeting_config?.title,
        subtitle: meta?.greeting_config?.subtitle,
        body: meta?.greeting_config?.body || msg.content,
        cta: meta?.cta,
        delayMs: meta?.delay_ms,
        channel: meta?.channel,
      });
    } else if (msg.role === "assistant") {
      const children: LLMCallSubItem[] = [];
      const childIndexById: Record<string, number> = {};

      const contentId = `${msg.id}-content`;
      const contentSubItem: ContentSubItem = {
        type: "content",
        id: contentId,
        text: msg.content,
        ts: Date.now(),
      };
      childIndexById[contentId] = children.length;
      children.push(contentSubItem);

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

// ==================== 兼容旧组件的类型别名（重新导出） ====================

export interface ReasoningItem {
  type: "assistant.reasoning";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  isOpen: boolean;
  ts: number;
}

export interface ContentItem {
  type: "assistant.content";
  id: string;
  turnId: string;
  llmCallId?: string;
  text: string;
  ts: number;
}

export interface ProductsItem {
  type: "assistant.products";
  id: string;
  turnId: string;
  products: Product[];
  ts: number;
}

export interface TodosItem {
  type: "assistant.todos";
  id: string;
  turnId: string;
  todos: TodoItem[];
  ts: number;
}

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
