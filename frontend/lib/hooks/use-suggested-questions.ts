"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getPublicSuggestedQuestions,
  recordSuggestedQuestionClick,
  type SuggestedQuestionsPublicResponse,
} from "@/lib/api/agents";

interface UseSuggestedQuestionsOptions {
  agentId: string | undefined;
  enabled?: boolean;
}

interface UseSuggestedQuestionsReturn {
  questions: SuggestedQuestionsPublicResponse;
  isLoading: boolean;
  error: string | null;
  trackClick: (questionId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const EMPTY_QUESTIONS: SuggestedQuestionsPublicResponse = {
  welcome: [],
  input: [],
};

export function useSuggestedQuestions(
  options: UseSuggestedQuestionsOptions
): UseSuggestedQuestionsReturn {
  const { agentId, enabled = true } = options;

  const [questions, setQuestions] =
    useState<SuggestedQuestionsPublicResponse>(EMPTY_QUESTIONS);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQuestions = useCallback(async () => {
    if (!agentId || !enabled) {
      setQuestions(EMPTY_QUESTIONS);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const data = await getPublicSuggestedQuestions(agentId);
      setQuestions(data);
    } catch (e) {
      console.error("获取推荐问题失败:", e);
      setError(e instanceof Error ? e.message : "获取推荐问题失败");
      setQuestions(EMPTY_QUESTIONS);
    } finally {
      setIsLoading(false);
    }
  }, [agentId, enabled]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const trackClick = useCallback(async (questionId: string) => {
    try {
      await recordSuggestedQuestionClick(questionId);
    } catch (e) {
      // 点击统计失败不影响用户体验，静默处理
      console.debug("记录点击失败:", e);
    }
  }, []);

  return {
    questions,
    isLoading,
    error,
    trackClick,
    refresh: fetchQuestions,
  };
}
