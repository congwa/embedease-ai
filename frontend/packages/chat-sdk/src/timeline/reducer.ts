/**
 * Timeline reducer 函数
 */

import type { ChatEvent } from "../core/events";
import type {
  TimelineState,
  LLMCallClusterItem,
  ToolCallItem,
  ErrorItem,
  FinalItem,
  MemoryEventItem,
  SupportEventItem,
  SkillActivatedItem,
  ReasoningSubItem,
  ContentSubItem,
  ProductsSubItem,
  TodosSubItem,
  ContextSummarizedSubItem,
} from "./types";
import {
  getToolLabel,
  insertItem,
  updateItemById,
  getCurrentLlmCluster,
  appendSubItemToCurrentCluster,
  updateSubItemInCurrentCluster,
  appendSubItemToCurrentToolCall,
  getLastSubItemOfType,
  removeWaitingItem,
} from "./helpers";

/** 处理 support.* 事件（不依赖 turnId） */
function handleSupportEvent(
  state: TimelineState,
  event: ChatEvent,
  turnId: string,
  now: number
): TimelineState {
  switch (event.type) {
    case "support.handoff_started":
    case "support.handoff_ended":
    case "support.human_message":
    case "support.human_mode":
    case "support.connected": {
      const eventType = event.type.replace(
        "support.",
        ""
      ) as SupportEventItem["eventType"];
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

    default:
      return state;
  }
}

export function timelineReducer(
  state: TimelineState,
  event: ChatEvent
): TimelineState {
  const turnId = state.activeTurn.turnId;
  const now = Date.now();

  // support.* 事件不依赖 turnId，始终处理
  if (event.type.startsWith("support.")) {
    return handleSupportEvent(state, event, turnId || `ws-${now}`, now);
  }

  // 其他事件需要 turnId
  if (!turnId) return state;

  switch (event.type) {
    case "meta.start": {
      const payload = event.payload as { assistant_message_id?: string };
      const oldTurnId = turnId;
      const newTurnId = payload.assistant_message_id;

      if (newTurnId && newTurnId !== oldTurnId) {
        const oldWaitingId = `waiting-${oldTurnId}`;
        const newWaitingId = `waiting-${newTurnId}`;

        const timeline = state.timeline.map((item) => {
          if (item.turnId === oldTurnId) {
            if (item.type === "waiting" && item.id === oldWaitingId) {
              return { ...item, id: newWaitingId, turnId: newTurnId };
            }
            return { ...item, turnId: newTurnId };
          }
          return item;
        });
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
      const stateWithoutWaiting = removeWaitingItem(state, turnId);

      const payload = event.payload as {
        llm_call_id?: string;
        message_count?: number;
      };
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
      const payload = event.payload as {
        llm_call_id?: string;
        elapsed_ms?: number;
        error?: string;
      };
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
      const payload = event.payload as { content?: string; reasoning?: string };

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

      const llmClusters = newState.timeline.filter(
        (item): item is LLMCallClusterItem =>
          item.type === "llm.call.cluster" && item.turnId === turnId
      );

      if (llmClusters.length > 0) {
        const lastCluster = llmClusters[llmClusters.length - 1];
        const hasContent = lastCluster.children.some(
          (child) => child.type === "content"
        );
        const reasoningItems = lastCluster.children.filter(
          (child): child is ReasoningSubItem => child.type === "reasoning"
        );

        if (!hasContent && reasoningItems.length > 0) {
          const reasoningText = reasoningItems.map((r) => r.text).join("");

          const contentSubItem: ContentSubItem = {
            type: "content",
            id: crypto.randomUUID(),
            text: reasoningText,
            ts: now,
          };

          newState = updateItemById(newState, lastCluster.id, (cluster) => {
            if (cluster.type !== "llm.call.cluster") return cluster;
            const newChildren = cluster.children.filter(
              (child) => child.type !== "reasoning"
            );
            newChildren.push(contentSubItem);
            return {
              ...cluster,
              children: newChildren,
              childIndexById: {
                ...Object.fromEntries(
                  newChildren.map((child, idx) => [child.id, idx])
                ),
              },
            };
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
      const eventType = event.type.replace(
        "memory.",
        ""
      ) as MemoryEventItem["eventType"];
      const item: MemoryEventItem = {
        type: "memory.event",
        id: `memory:${event.seq}`,
        turnId,
        eventType,
        ts: now,
      };
      return insertItem(state, item);
    }

    case "error": {
      const payload = event.payload as { message?: string };
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
      const payload = event.payload as { delta?: string };
      const delta = payload.delta;
      if (!delta) return state;

      const cluster = getCurrentLlmCluster(state);
      if (!cluster) return state;

      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(
        cluster,
        "reasoning"
      );
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
      const payload = event.payload as { delta?: string };
      const delta = payload.delta;
      if (!delta) return state;

      const cluster = getCurrentLlmCluster(state);
      if (!cluster) return state;

      let newState = state;
      const lastReasoning = getLastSubItemOfType<ReasoningSubItem>(
        cluster,
        "reasoning"
      );
      if (lastReasoning && lastReasoning.isOpen) {
        newState = updateSubItemInCurrentCluster(
          newState,
          lastReasoning.id,
          (sub) => {
            if (sub.type !== "reasoning") return sub;
            return { ...sub, isOpen: false };
          }
        );
      }

      const updatedCluster = getCurrentLlmCluster(newState);
      if (!updatedCluster) return newState;
      const lastContent = getLastSubItemOfType<ContentSubItem>(
        updatedCluster,
        "content"
      );
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
      const payload = event.payload as {
        tool_call_id?: string;
        name: string;
        input?: unknown;
      };
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
      const payload = event.payload as {
        tool_call_id?: string;
        status?: string;
        count?: number;
        error?: string;
      };
      const toolCallId = payload.tool_call_id || state.activeTurn.currentToolCallId;
      if (!toolCallId) return state;

      const newState = updateItemById(state, toolCallId, (item) => {
        if (item.type !== "tool.call") return item;
        const elapsedMs = Date.now() - item.startedAt;
        const status =
          (payload.status as ToolCallItem["status"]) ||
          (payload.error ? "error" : "success");
        return {
          ...item,
          status,
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
      const payload = event.payload as { items?: unknown[] };
      const products = payload.items;
      if (!products || products.length === 0) return state;

      const subItem: ProductsSubItem = {
        type: "products",
        id: `products:${event.seq}`,
        products: products as ProductsSubItem["products"],
        ts: now,
      };

      if (state.activeTurn.currentToolCallId) {
        return appendSubItemToCurrentToolCall(state, subItem);
      }
      return appendSubItemToCurrentCluster(state, subItem);
    }

    case "assistant.todos": {
      const payload = event.payload as { todos?: unknown[] };
      const todos = payload.todos;
      if (!todos || todos.length === 0) return state;

      const subItem: TodosSubItem = {
        type: "todos",
        id: `todos:${event.seq}`,
        todos: todos as TodosSubItem["todos"],
        ts: now,
      };

      if (state.activeTurn.currentToolCallId) {
        return appendSubItemToCurrentToolCall(state, subItem);
      }
      return appendSubItemToCurrentCluster(state, subItem);
    }

    case "context.summarized": {
      const payload = event.payload as {
        messages_before: number;
        messages_after: number;
        tokens_before?: number;
        tokens_after?: number;
      };
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

    case "skill.activated": {
      const payload = event.payload as {
        skill_id: string;
        skill_name: string;
        trigger_type: "keyword" | "intent" | "manual";
        trigger_keyword?: string;
      };
      const skillItem: SkillActivatedItem = {
        type: "skill.activated",
        id: `skill:${payload.skill_id}:${event.seq}`,
        turnId,
        skillId: payload.skill_id,
        skillName: payload.skill_name,
        triggerType: payload.trigger_type,
        triggerKeyword: payload.trigger_keyword,
        ts: now,
      };
      return insertItem(state, skillItem);
    }

    default:
      return state;
  }
}
