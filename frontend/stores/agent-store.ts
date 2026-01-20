/**
 * Agent 配置状态管理 Store
 */

import { create } from "zustand";

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  type: "product" | "faq" | "kb" | "custom";
  status: "enabled" | "disabled";
  is_default: boolean;
  is_supervisor: boolean;
  mode_default: string;
  created_at: string;
  updated_at: string;
  knowledge_config?: {
    id: string;
    name: string;
    type: string;
  } | null;
}

interface AgentState {
  agents: Agent[];
  isLoading: boolean;
  error: string | null;

  activeAgent: () => Agent | null;
  getAgentById: (id: string) => Agent | undefined;

  fetchAgents: () => Promise<void>;
  activateAgent: (agentId: string) => Promise<boolean>;
  refresh: () => Promise<void>;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  agents: [],
  isLoading: true,
  error: null,

  activeAgent: () => get().agents.find((a) => a.is_default) || null,

  getAgentById: (id: string) => get().agents.find((a) => a.id === id),

  fetchAgents: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await fetch("/api/v1/admin/agents");
      if (!response.ok) {
        throw new Error("获取 Agent 列表失败");
      }
      const data = await response.json();
      set({ agents: data.items || [], isLoading: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "未知错误",
        isLoading: false,
      });
    }
  },

  activateAgent: async (agentId: string) => {
    try {
      const response = await fetch(`/api/v1/admin/agents/${agentId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_default: true }),
      });
      if (!response.ok) {
        throw new Error("激活 Agent 失败");
      }
      await get().fetchAgents();
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "激活失败" });
      return false;
    }
  },

  refresh: async () => {
    await get().fetchAgents();
  },
}));
