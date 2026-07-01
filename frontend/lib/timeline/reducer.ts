/**
 * Timeline reducer 函数
 *
 * 基于 SDK v0.2.0 composeReducers 架构：
 * - 业务扩展事件由 businessReducer 处理（support 扩展、assistant.final 推理转内容）
 * - 基础事件委托给 SDK 内置 timelineReducer
 */

import {
  composeReducers as sdkComposeReducers,
  type CustomReducer as SDKCustomReducer,
} from "@embedease/chat-sdk";
import type { ChatEvent } from "@/types/chat";
import type {
  TimelineState,
  ComplaintEventItem,
  LLMCallClusterItem,
  FinalItem,
  SupportEventItem,
  ReasoningSubItem,
  ContentSubItem,
} from "./types";
import {
  insertItem,
  removeWaitingItem,
  updateItemById,
} from "./helpers";


// ==================== 业务扩展：support.* 事件 ====================


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
      const payload = event.payload as { message_ids: string[] };
      if (!payload.message_ids || payload.message_ids.length === 0) return state;
      const deletedSet = new Set(payload.message_ids);
      const timeline = state.timeline.filter((item) => !deletedSet.has(item.id));
      const indexById: Record<string, number> = {};
      timeline.forEach((item, i) => {
        indexById[item.id] = i;
      });
      return { ...state, timeline, indexById };
    }

    default:
      return state;
  }
}


// ==================== 业务扩展：complaint.* 事件 ====================


/**
 * 生成客诉事件的展示文案。
 *
 * 这个函数用于把后端 complaint 事件翻译成用户可理解的阶段说明。
 */
function buildComplaintLabel(event: ChatEvent): { label: string; description?: string } {
  const payload = event.payload as {
    ticket?: { primary_issue_tag?: string | null; status?: string };
    task?: { task_type?: string; agent_tag?: string; goal?: string; failure_reason?: string | null };
    score?: number;
    reasons?: string[];
    handoff_reason?: string;
    message?: string;
  };

  switch (event.type) {
    case "complaint.ticket.created":
      return { label: "已创建问题单", description: payload.ticket?.primary_issue_tag || "系统已开始围绕当前问题单推进处理" };
    case "complaint.ticket.merged":
      return { label: "已归并到当前问题单", description: "您刚才的补充会继续挂到同一问题单处理" };
    case "complaint.secondary_issue.detected":
      return { label: "识别到次级问题", description: "系统已记录新的附带诉求，避免后续遗漏" };
    case "complaint.task.created":
      return { label: "已创建处理任务", description: payload.task?.goal };
    case "complaint.task.started":
      return { label: `开始执行 ${payload.task?.task_type || "任务"}`, description: payload.task?.agent_tag || undefined };
    case "complaint.task.completed":
      return { label: `完成 ${payload.task?.task_type || "任务"}`, description: payload.task?.failure_reason || payload.task?.goal };
    case "complaint.review.pending":
      return { label: "进入质量审查", description: "候选回复正在做合规与质量检查" };
    case "complaint.review.passed":
      return { label: "审查通过", description: typeof payload.score === "number" ? `质量分 ${payload.score}` : "当前回复已允许对外发送" };
    case "complaint.review.rejected":
      return { label: "审查未通过", description: payload.reasons?.[0] || "系统已要求返工或升级处理" };
    case "complaint.handoff_requested":
      return { label: "已请求人工接手", description: payload.handoff_reason || payload.message || "客服接手时会直接看到当前问题摘要" };
    case "complaint.blocked":
      return { label: "当前处理被阻塞", description: payload.reasons?.[0] || "系统已记录阻塞原因" };
    default:
      return { label: "问题单状态已更新" };
  }
}


/**
 * 处理 complaint.* 事件。
 *
 * 这个函数用于在客诉编排开始后移除 waiting 状态，并把处理阶段插入到时间线中。
 */
function handleComplaintEvent(
  state: TimelineState,
  event: ChatEvent,
  turnId: string,
  now: number
): TimelineState {
  const stateWithoutWaiting = turnId ? removeWaitingItem(state, turnId) : state;

  if (event.type === "complaint.ticket.updated") {
    return stateWithoutWaiting;
  }

  const payload = event.payload as {
    task?: { task_type?: string; agent_tag?: string };
    score?: number;
  };
  const eventType = event.type.replace("complaint.", "").replace(/\./g, "_") as ComplaintEventItem["eventType"];
  const { label, description } = buildComplaintLabel(event);

  const item: ComplaintEventItem = {
    type: "complaint.event",
    id: `complaint:${event.seq || crypto.randomUUID()}`,
    turnId,
    eventType,
    label,
    description,
    taskType: payload.task?.task_type,
    agentTag: payload.task?.agent_tag,
    reviewScore: payload.score,
    ts: now,
  };
  return insertItem(stateWithoutWaiting, item);
}


// ==================== 业务扩展：assistant.final 推理转内容修复 ====================


/**
 * 处理 assistant.final 事件（覆盖 SDK 默认行为）
 *
 * 额外逻辑：如果最后一个 LLM cluster 只有 reasoning 没有 content，
 * 把 reasoning 的内容作为 content 添加（硅基流动模型修复）
 */
function handleAssistantFinal(
  state: TimelineState,
  event: ChatEvent,
  turnId: string,
  now: number
): TimelineState {
  const payload = event.payload as { content?: string; reasoning?: string };

  console.log("[reducer] assistant.final received:", {
    content: payload.content,
    reasoningLength: payload.reasoning?.length,
    reasoningPreview: payload.reasoning?.slice(0, 100),
  });

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

  // 检查最后一个 LLM cluster 是否只有 reasoning 没有 content
  const llmClusters = newState.timeline.filter(
    (item): item is LLMCallClusterItem =>
      item.type === "llm.call.cluster" && item.turnId === turnId
  );

  if (llmClusters.length > 0) {
    const lastCluster = llmClusters[llmClusters.length - 1];
    const hasContent = lastCluster.children.some((child) => child.type === "content");
    const reasoningItems = lastCluster.children.filter(
      (child): child is ReasoningSubItem => child.type === "reasoning"
    );

    if (!hasContent && reasoningItems.length > 0) {
      const reasoningText = reasoningItems.map((r) => r.text).join("");
      console.log("[reducer] Converting reasoning to content:", reasoningText.slice(0, 100));

      const contentSubItem: ContentSubItem = {
        type: "content",
        id: crypto.randomUUID(),
        text: reasoningText,
        ts: now,
      };

      newState = updateItemById(newState, lastCluster.id, (cluster) => {
        if (cluster.type !== "llm.call.cluster") return cluster;
        const newChildren = cluster.children.filter((child) => child.type !== "reasoning");
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


// ==================== 组合 Reducer ====================


/**
 * 业务 reducer：处理项目特有的扩展事件
 *
 * 符合 SDK CustomReducer 协议：
 * - 返回 TimelineState 表示已处理
 * - 返回 null 表示未处理，交给 SDK 内置 reducer 兜底
 *
 * 处理：
 * - support.* 扩展事件（消息撤回/编辑/删除等）
 * - assistant.final 推理转内容修复（硅基流动模型）
 */
const businessReducer: SDKCustomReducer = (state, event) => {
  const localState = state as unknown as TimelineState;
  const chatEvent = event as ChatEvent;
  const turnId = localState.activeTurn.turnId;
  const now = Date.now();

  // support.* 事件不依赖 turnId，始终由业务 reducer 处理
  if (chatEvent.type.startsWith("support.")) {
    return handleSupportEvent(localState, chatEvent, turnId || `ws-${now}`, now) as unknown as ReturnType<SDKCustomReducer>;
  }

  if (chatEvent.type.startsWith("complaint.") && turnId) {
    return handleComplaintEvent(localState, chatEvent, turnId, now) as unknown as ReturnType<SDKCustomReducer>;
  }

  // assistant.final 覆盖 SDK 行为（需要 turnId）
  if (chatEvent.type === "assistant.final" && turnId) {
    return handleAssistantFinal(localState, chatEvent, turnId, now) as unknown as ReturnType<SDKCustomReducer>;
  }

  // 其他事件不处理，交给 SDK 内置 reducer
  return null;
};


/**
 * 组合后的 Timeline reducer
 *
 * 使用 SDK composeReducers：businessReducer → SDK 内置 timelineReducer
 * - businessReducer 处理项目特有事件，返回 null 表示未处理
 * - SDK timelineReducer 处理所有基础事件（meta.start, llm.call.*, tool.*, 等）
 */
const _composedReducer = sdkComposeReducers(businessReducer);

export function timelineReducer(state: TimelineState, event: ChatEvent): TimelineState {
  return _composedReducer(
    state as Parameters<typeof _composedReducer>[0],
    event as Parameters<typeof _composedReducer>[1]
  ) as unknown as TimelineState;
}
