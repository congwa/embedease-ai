"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Network, ChevronRight } from "lucide-react";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/admin";

export default function AgentOverviewPage() {
  const params = useParams();
  const agentId = params.agentId as string;
  const { agent } = useAgentDetail({ agentId });

  if (!agent) return null;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* 系统提示词 */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">系统提示词</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-64 overflow-auto rounded-lg bg-zinc-50 p-4 text-sm whitespace-pre-wrap dark:bg-zinc-900">
            {agent.system_prompt}
          </pre>
        </CardContent>
      </Card>

      {/* 基础配置 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">基础配置</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between">
            <span className="text-sm text-zinc-500">Agent ID</span>
            <code className="text-xs">{agent.id}</code>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-zinc-500">默认模式</span>
            <Badge variant="outline">{agent.mode_default}</Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-zinc-500">响应格式</span>
            <span className="text-sm">{agent.response_format || "默认"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-sm text-zinc-500">状态</span>
            <StatusBadge enabled={agent.status === "enabled"} />
          </div>
        </CardContent>
      </Card>

      {/* 中间件配置 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">中间件开关</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {agent.middleware_flags ? (
            Object.entries(agent.middleware_flags).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-sm text-zinc-500">{key}</span>
                <StatusBadge enabled={!!value} />
              </div>
            ))
          ) : (
            <p className="text-sm text-zinc-400">使用全局默认配置</p>
          )}
        </CardContent>
      </Card>

      {/* 工具策略 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">工具策略</CardTitle>
        </CardHeader>
        <CardContent>
          {agent.tool_policy ? (
            <pre className="rounded-lg bg-zinc-50 p-3 text-xs dark:bg-zinc-900">
              {JSON.stringify(agent.tool_policy, null, 2)}
            </pre>
          ) : (
            <p className="text-sm text-zinc-400">使用默认策略</p>
          )}
        </CardContent>
      </Card>

      {/* 工具类别 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">工具类别</CardTitle>
        </CardHeader>
        <CardContent>
          {agent.tool_categories && agent.tool_categories.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {agent.tool_categories.map((cat) => (
                <Badge key={cat} variant="secondary">
                  {cat}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-400">未配置工具类别</p>
          )}
        </CardContent>
      </Card>

      {/* Supervisor 配置 */}
      <Card className={agent.is_supervisor ? "border-orange-200 bg-orange-50/30 dark:border-orange-900 dark:bg-orange-950/20" : ""}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className={`h-4 w-4 ${agent.is_supervisor ? "text-orange-500" : "text-zinc-400"}`} />
              <CardTitle className="text-base">多 Agent 编排</CardTitle>
            </div>
            <Link href={`/admin/agents/${agentId}/supervisor`}>
              <Button variant="ghost" size="sm" className="h-7 text-xs">
                配置
                <ChevronRight className="ml-1 h-3 w-3" />
              </Button>
            </Link>
          </div>
          <CardDescription>
            {agent.is_supervisor ? "已启用 Supervisor 模式" : "未启用"}
          </CardDescription>
        </CardHeader>
        {agent.is_supervisor && (
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-zinc-500">子 Agent 数量</span>
              <Badge variant="secondary">{agent.sub_agents?.length || 0}</Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-zinc-500">路由策略</span>
              <Badge variant="outline">{agent.routing_policy?.type || "未配置"}</Badge>
            </div>
            {agent.sub_agents && agent.sub_agents.length > 0 && (
              <div className="pt-2 border-t">
                <span className="text-xs text-zinc-500 block mb-2">子 Agent 列表</span>
                <div className="flex flex-wrap gap-1">
                  {agent.sub_agents.map((sa) => (
                    <Badge key={sa.agent_id} variant="secondary" className="text-xs">
                      {sa.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
