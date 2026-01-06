"use client";

/**
 * Agent 上下文管理
 * 
 * 提供当前激活 Agent 的全局状态管理，支持：
 * - 获取当前激活的 Agent
 * - 切换激活的 Agent
 * - Agent 列表缓存
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";

export interface Agent {
  id: string;
  name: string;
  description: string | null;
  type: "product" | "faq" | "kb" | "custom";
  status: "enabled" | "disabled";
  is_default: boolean;
  mode_default: string;
  created_at: string;
  updated_at: string;
  knowledge_config?: {
    id: string;
    name: string;
    type: string;
  } | null;
}

interface AgentContextValue {
  // 当前激活的 Agent（is_default = true）
  activeAgent: Agent | null;
  // 所有 Agent 列表
  agents: Agent[];
  // 加载状态
  isLoading: boolean;
  // 错误信息
  error: string | null;
  // 刷新 Agent 列表
  refresh: () => Promise<void>;
  // 切换激活的 Agent
  activateAgent: (agentId: string) => Promise<boolean>;
  // 根据 ID 获取 Agent
  getAgentById: (id: string) => Agent | undefined;
}

const AgentContext = createContext<AgentContextValue | null>(null);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const activeAgent = agents.find((a) => a.is_default) || null;

  const fetchAgents = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch("/api/v1/admin/agents");
      if (!response.ok) {
        throw new Error("获取 Agent 列表失败");
      }

      const data = await response.json();
      setAgents(data.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const activateAgent = useCallback(
    async (agentId: string): Promise<boolean> => {
      try {
        const response = await fetch(`/api/v1/admin/agents/${agentId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_default: true }),
        });

        if (!response.ok) {
          throw new Error("激活 Agent 失败");
        }

        // 刷新列表
        await fetchAgents();
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "激活失败");
        return false;
      }
    },
    [fetchAgents]
  );

  const getAgentById = useCallback(
    (id: string) => agents.find((a) => a.id === id),
    [agents]
  );

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  return (
    <AgentContext.Provider
      value={{
        activeAgent,
        agents,
        isLoading,
        error,
        refresh: fetchAgents,
        activateAgent,
        getAgentById,
      }}
    >
      {children}
    </AgentContext.Provider>
  );
}

export function useAgentContext() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error("useAgentContext must be used within AgentProvider");
  }
  return context;
}

/**
 * 获取当前激活的 Agent
 */
export function useActiveAgent() {
  const { activeAgent, isLoading, error } = useAgentContext();
  return { activeAgent, isLoading, error };
}
