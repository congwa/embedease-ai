"use client";

import { useState, useMemo } from "react";
import { Plus, Bot, RefreshCw } from "lucide-react";
import { useAgents } from "@/lib/hooks/use-agents";
import {
  PageHeader,
  LoadingState,
  ErrorAlert,
  EmptyState,
} from "@/components/admin";
import { AgentList, AgentFilterBar, CreateAgentDialog } from "@/components/admin/agents";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface AgentFilters {
  status?: string;
  type?: string;
  searchQuery?: string;
}

export default function AgentsPage() {
  const { agents, isLoading, error, loadAgents } = useAgents();
  const [filters, setFilters] = useState<AgentFilters>({});

  const filteredAgents = useMemo(() => {
    return agents.filter((agent) => {
      const matchesStatus =
        !filters.status || agent.status === filters.status;
      const matchesType = !filters.type || agent.type === filters.type;
      const matchesSearch =
        !filters.searchQuery ||
        agent.name.toLowerCase().includes(filters.searchQuery.toLowerCase()) ||
        agent.description?.toLowerCase().includes(filters.searchQuery.toLowerCase());
      return matchesStatus && matchesType && matchesSearch;
    });
  }, [agents, filters]);

  const stats = useMemo(() => {
    const enabled = agents.filter((a) => a.status === "enabled").length;
    const defaultAgent = agents.find((a) => a.is_default);
    return {
      total: agents.length,
      enabled,
      disabled: agents.length - enabled,
      defaultName: defaultAgent?.name || "-",
    };
  }, [agents]);

  if (isLoading) {
    return <LoadingState text="加载 Agent 列表..." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader
          title="Agent 中心"
          description="管理和配置所有智能体"
        />
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadAgents}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <CreateAgentDialog onCreated={loadAgents} />
        </div>
      </div>

      <ErrorAlert error={error} />

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">Agent 总数</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <Bot className="h-8 w-8 text-zinc-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">已启用</p>
                <p className="text-2xl font-bold text-green-600">{stats.enabled}</p>
              </div>
              <div className="h-8 w-8 rounded-full bg-green-100" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">已禁用</p>
                <p className="text-2xl font-bold text-zinc-400">{stats.disabled}</p>
              </div>
              <div className="h-8 w-8 rounded-full bg-zinc-100" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div>
              <p className="text-sm text-zinc-500">默认 Agent</p>
              <p className="text-lg font-medium truncate">{stats.defaultName}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <AgentFilterBar filters={filters} onFilterChange={setFilters} />

      {filteredAgents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="暂无 Agent"
          description={
            agents.length > 0
              ? "没有匹配筛选条件的 Agent"
              : "创建您的第一个智能体开始使用"
          }
          action={
            agents.length === 0 && (
              <CreateAgentDialog onCreated={loadAgents} />
            )
          }
        />
      ) : (
        <AgentList agents={filteredAgents} />
      )}
    </div>
  );
}
