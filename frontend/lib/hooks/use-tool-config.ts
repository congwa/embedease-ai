"use client";

import { useState, useCallback, useMemo } from "react";
import type { ToolCategoriesConfig, ToolPolicyConfig } from "@/components/admin/tools";
import { DEFAULT_TOOL_POLICY, DEFAULT_CATEGORIES_BY_TYPE } from "@/components/admin/tools";

export interface UseToolConfigOptions {
  initialCategories?: string[];
  initialPolicy?: Partial<ToolPolicyConfig>;
  agentType?: string;
}

export interface UseToolConfigReturn {
  categories: ToolCategoriesConfig;
  policy: ToolPolicyConfig;
  setCategories: (config: ToolCategoriesConfig) => void;
  updatePolicy: (patch: Partial<ToolPolicyConfig>) => void;
  expandedCategories: Set<string>;
  toggleCategoryExpand: (cat: string) => void;
  hasChanges: boolean;
  reset: () => void;
}

export function useToolConfig(options: UseToolConfigOptions = {}): UseToolConfigReturn {
  const { initialCategories, initialPolicy, agentType } = options;

  const defaultCategories = useMemo(() => {
    if (initialCategories && initialCategories.length > 0) {
      return initialCategories;
    }
    if (agentType && DEFAULT_CATEGORIES_BY_TYPE[agentType]) {
      return DEFAULT_CATEGORIES_BY_TYPE[agentType];
    }
    return [];
  }, [initialCategories, agentType]);

  const defaultPolicy = useMemo(
    () => ({ ...DEFAULT_TOOL_POLICY, ...initialPolicy }),
    [initialPolicy]
  );

  const [categories, setCategoriesState] = useState<ToolCategoriesConfig>({
    categories: defaultCategories,
  });

  const [policy, setPolicyState] = useState<ToolPolicyConfig>(defaultPolicy);

  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const setCategories = useCallback((config: ToolCategoriesConfig) => {
    setCategoriesState(config);
  }, []);

  const updatePolicy = useCallback((patch: Partial<ToolPolicyConfig>) => {
    setPolicyState((prev) => ({ ...prev, ...patch }));
  }, []);

  const toggleCategoryExpand = useCallback((cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  }, []);

  const hasChanges = useMemo(() => {
    const categoriesChanged =
      JSON.stringify([...categories.categories].sort()) !==
      JSON.stringify([...defaultCategories].sort());
    const policyChanged = JSON.stringify(policy) !== JSON.stringify(defaultPolicy);
    return categoriesChanged || policyChanged;
  }, [categories, policy, defaultCategories, defaultPolicy]);

  const reset = useCallback(() => {
    setCategoriesState({ categories: defaultCategories });
    setPolicyState(defaultPolicy);
  }, [defaultCategories, defaultPolicy]);

  return {
    categories,
    policy,
    setCategories,
    updatePolicy,
    expandedCategories,
    toggleCategoryExpand,
    hasChanges,
    reset,
  };
}
