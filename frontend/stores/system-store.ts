/**
 * 系统功能状态管理 Store
 */

import { create } from "zustand";

export interface FeatureStatus {
  enabled: boolean;
  status: "healthy" | "degraded" | "unhealthy" | "disabled" | "unknown";
  message?: string | null;
  last_error?: string | null;
}

export interface CrawlerFeature extends FeatureStatus {}

export interface MemoryFeature {
  enabled: boolean;
  store_enabled: boolean;
  fact_enabled: boolean;
  graph_enabled: boolean;
}

export interface NotificationFeature {
  wework: FeatureStatus;
  webhook: FeatureStatus;
}

export interface SystemFeatures {
  crawler: CrawlerFeature;
  memory: MemoryFeature;
  rerank: FeatureStatus;
  notifications: NotificationFeature;
}

const DEFAULT_FEATURES: SystemFeatures = {
  crawler: {
    enabled: false,
    status: "unknown",
    message: null,
    last_error: null,
  },
  memory: {
    enabled: false,
    store_enabled: false,
    fact_enabled: false,
    graph_enabled: false,
  },
  rerank: {
    enabled: false,
    status: "unknown",
    message: null,
    last_error: null,
  },
  notifications: {
    wework: {
      enabled: false,
      status: "unknown",
      message: null,
      last_error: null,
    },
    webhook: {
      enabled: false,
      status: "unknown",
      message: null,
      last_error: null,
    },
  },
};

interface SystemState {
  features: SystemFeatures;
  isLoading: boolean;
  error: string | null;

  fetchFeatures: () => Promise<void>;
  isFeatureEnabled: (feature: keyof SystemFeatures) => boolean;
}

export const useSystemStore = create<SystemState>((set, get) => ({
  features: DEFAULT_FEATURES,
  isLoading: true,
  error: null,

  fetchFeatures: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await fetch("/api/v1/system/features");
      if (!response.ok) {
        throw new Error(`获取功能状态失败: ${response.statusText}`);
      }
      const data = await response.json();
      set({ features: data, isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "未知错误",
        isLoading: false,
        features: DEFAULT_FEATURES,
      });
    }
  },

  isFeatureEnabled: (feature: keyof SystemFeatures) => {
    const featureData = get().features[feature];
    return typeof featureData === "object" && "enabled" in featureData
      ? featureData.enabled
      : false;
  },
}));
