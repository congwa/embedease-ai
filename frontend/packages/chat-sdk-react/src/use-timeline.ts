/**
 * useTimeline Hook
 *
 * Timeline 状态管理 Hook
 */

import { useCallback, useState } from "react";
import {
  createInitialState,
  addUserMessage as sdkAddUserMessage,
  startAssistantTurn as sdkStartAssistantTurn,
  clearTurn as sdkClearTurn,
  endTurn as sdkEndTurn,
  timelineReducer as sdkTimelineReducer,
  historyToTimeline as sdkHistoryToTimeline,
  type TimelineState,
  type TimelineItem,
  type ChatEvent,
  type ImageAttachment,
  type HistoryMessage,
} from "@embedease/chat-sdk";

export interface UseTimelineOptions {
  /** 初始状态 */
  initialState?: TimelineState;
}

export interface UseTimelineReturn {
  /** 当前状态 */
  state: TimelineState;

  /** 时间线项列表 */
  timeline: TimelineItem[];

  /** 处理事件 */
  dispatch: (event: ChatEvent) => void;

  /** 添加用户消息 */
  addUserMessage: (
    id: string,
    content: string,
    images?: ImageAttachment[]
  ) => void;

  /** 开始助手回复 */
  startAssistantTurn: (turnId: string) => void;

  /** 清除 Turn */
  clearTurn: (turnId: string) => void;

  /** 结束 Turn */
  endTurn: () => void;

  /** 重置状态 */
  reset: () => void;

  /** 从历史消息初始化 */
  initFromHistory: (messages: HistoryMessage[]) => void;

  /** 设置状态 */
  setState: (state: TimelineState) => void;

  /** 当前 Turn ID */
  currentTurnId: string | null;

  /** 是否正在流式响应 */
  isStreaming: boolean;
}

export function useTimeline(options?: UseTimelineOptions): UseTimelineReturn {
  const [state, setStateInternal] = useState<TimelineState>(
    options?.initialState ?? createInitialState()
  );

  const dispatch = useCallback((event: ChatEvent) => {
    setStateInternal((prev) => sdkTimelineReducer(prev, event));
  }, []);

  const addUserMessage = useCallback(
    (id: string, content: string, images?: ImageAttachment[]) => {
      setStateInternal((prev) => sdkAddUserMessage(prev, id, content, images));
    },
    []
  );

  const startAssistantTurn = useCallback((turnId: string) => {
    setStateInternal((prev) => sdkStartAssistantTurn(prev, turnId));
  }, []);

  const clearTurn = useCallback((turnId: string) => {
    setStateInternal((prev) => sdkClearTurn(prev, turnId));
  }, []);

  const endTurn = useCallback(() => {
    setStateInternal((prev) => sdkEndTurn(prev));
  }, []);

  const reset = useCallback(() => {
    setStateInternal(createInitialState());
  }, []);

  const initFromHistory = useCallback((messages: HistoryMessage[]) => {
    setStateInternal(sdkHistoryToTimeline(messages));
  }, []);

  const setState = useCallback((newState: TimelineState) => {
    setStateInternal(newState);
  }, []);

  return {
    state,
    timeline: state.timeline,
    dispatch,
    addUserMessage,
    startAssistantTurn,
    clearTurn,
    endTurn,
    reset,
    initFromHistory,
    setState,
    currentTurnId: state.activeTurn.turnId,
    isStreaming: state.activeTurn.isStreaming,
  };
}
