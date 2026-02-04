/**
 * Timeline 公共 action 函数
 */

import type { ImageAttachment } from "../core/types";
import type {
  TimelineState,
  UserMessageItem,
  GreetingItem,
  WaitingItem,
} from "./types";
import { insertItem } from "./helpers";

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

export function startAssistantTurn(
  state: TimelineState,
  turnId: string
): TimelineState {
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

export function clearTurn(
  state: TimelineState,
  turnId: string
): TimelineState {
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
