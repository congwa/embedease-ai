/**
 * 系统模式状态管理 Store
 * 管理单Agent模式和Supervisor模式的切换与状态
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type SystemMode = "single" | "supervisor";

export interface SubAgentConfig {
  agentId: string;
  name: string;
  type: string;
  priority: number;
  keywords: string[];
  description: string;
  enabled: boolean;
}

export interface SupervisorConfig {
  enabled: boolean;
  defaultAgentId: string | null;
  subAgents: SubAgentConfig[];
  routingStrategy: "keyword" | "llm" | "hybrid";
  dispatchPrompt: string;
}

interface ModeState {
  mode: SystemMode;
  activeAgentId: string | null;
  supervisorConfig: SupervisorConfig | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setMode: (mode: SystemMode) => void;
  setActiveAgentId: (agentId: string | null) => void;
  setSupervisorConfig: (config: SupervisorConfig | null) => void;
  fetchModeState: () => Promise<void>;
  switchMode: (targetMode: SystemMode) => Promise<boolean>;
  updateSupervisorConfig: (config: Partial<SupervisorConfig>) => Promise<boolean>;
}

const DEFAULT_SUPERVISOR_CONFIG: SupervisorConfig = {
  enabled: false,
  defaultAgentId: null,
  subAgents: [],
  routingStrategy: "hybrid",
  dispatchPrompt: "",
};

export const useModeStore = create<ModeState>()(
  persist(
    (set, get) => ({
      mode: "single",
      activeAgentId: null,
      supervisorConfig: null,
      isLoading: false,
      error: null,

      setMode: (mode) => set({ mode }),

      setActiveAgentId: (agentId) => set({ activeAgentId: agentId }),

      setSupervisorConfig: (config) => set({ supervisorConfig: config }),

      fetchModeState: async () => {
        try {
          set({ isLoading: true, error: null });

          const response = await fetch("/api/v1/admin/quick-setup/state/mode");
          if (!response.ok) {
            throw new Error(`获取模式状态失败: ${response.statusText}`);
          }

          const data = await response.json();
          
          // 根据返回数据设置模式
          const mode: SystemMode = data.mode || "single";
          
          set({
            mode,
            supervisorConfig: data.supervisorConfig || DEFAULT_SUPERVISOR_CONFIG,
            isLoading: false,
          });
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "未知错误",
            isLoading: false,
          });
        }
      },

      switchMode: async (targetMode) => {
        try {
          set({ isLoading: true, error: null });

          const response = await fetch(`/api/v1/admin/quick-setup/state/mode/${targetMode}`, {
            method: "POST",
          });

          if (!response.ok) {
            throw new Error(`切换模式失败: ${response.statusText}`);
          }

          set({ mode: targetMode, isLoading: false });
          return true;
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "未知错误",
            isLoading: false,
          });
          return false;
        }
      },

      updateSupervisorConfig: async (config) => {
        try {
          set({ isLoading: true, error: null });

          const currentConfig = get().supervisorConfig || DEFAULT_SUPERVISOR_CONFIG;
          const newConfig = { ...currentConfig, ...config };

          const response = await fetch("/api/v1/admin/system-config/supervisor", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newConfig),
          });

          if (!response.ok) {
            throw new Error(`更新Supervisor配置失败: ${response.statusText}`);
          }

          set({ supervisorConfig: newConfig, isLoading: false });
          return true;
        } catch (err) {
          set({
            error: err instanceof Error ? err.message : "未知错误",
            isLoading: false,
          });
          return false;
        }
      },
    }),
    {
      name: "system-mode-storage",
      partialize: (state) => ({
        mode: state.mode,
        activeAgentId: state.activeAgentId,
      }),
    }
  )
);

// 辅助 Hook：获取当前是否为 Supervisor 模式
export const useIsSupervisorMode = () => {
  return useModeStore((state) => state.mode === "supervisor");
};

// 辅助 Hook：获取模式显示名称
export const useModeDisplayName = () => {
  return useModeStore((state) =>
    state.mode === "supervisor" ? "Supervisor 模式" : "单 Agent 模式"
  );
};
