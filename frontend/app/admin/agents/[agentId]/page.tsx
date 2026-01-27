"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { Network, ChevronRight, CheckCircle, XCircle, Wrench, Tag } from "lucide-react";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/admin";
import { getModeLabel, getMiddlewareLabel, getToolCategoryLabel } from "@/lib/config/labels";

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
            <Badge variant="outline">{getModeLabel(agent.mode_default)}</Badge>
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
            Object.entries(agent.middleware_flags).map(([key, value]) => {
              const info = getMiddlewareLabel(key);
              return (
                <div key={key} className="flex justify-between">
                  <span className="text-sm text-zinc-500">{info.label}</span>
                  <StatusBadge enabled={!!value} />
                </div>
              );
            })
          ) : (
            <p className="text-sm text-zinc-400">使用全局默认配置</p>
          )}
        </CardContent>
      </Card>

      {/* 工具策略 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-zinc-500" />
            <CardTitle className="text-base">工具调用策略</CardTitle>
          </div>
          <CardDescription>
            控制 Agent 如何使用工具回答问题
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {agent.tool_policy ? (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {agent.tool_policy.allow_direct_answer ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-zinc-300" />
                  )}
                  <span className="text-sm">允许直接回答</span>
                </div>
                <Badge variant={agent.tool_policy.allow_direct_answer ? "default" : "secondary"}
                       className={agent.tool_policy.allow_direct_answer ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : ""}>
                  {agent.tool_policy.allow_direct_answer ? "是" : "否"}
                </Badge>
              </div>
              <p className="text-xs text-zinc-400 ml-6">
                {agent.tool_policy.allow_direct_answer
                  ? "Agent 可以不调用工具直接回答简单问题"
                  : "Agent 必须调用工具后才能回答"}
              </p>
              <div className="flex items-center justify-between pt-2 border-t">
                <span className="text-sm">最少工具调用次数</span>
                <Badge variant="outline">
                  {agent.tool_policy.min_tool_calls === 0
                    ? "不限制"
                    : `至少 ${agent.tool_policy.min_tool_calls} 次`}
                </Badge>
              </div>
              {agent.tool_policy.fallback_tool && (
                <div className="flex items-center justify-between">
                  <span className="text-sm">备选工具</span>
                  <Badge variant="secondary">{String(agent.tool_policy.fallback_tool)}</Badge>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-zinc-400">使用默认策略</p>
          )}
        </CardContent>
      </Card>

      {/* 工具类别 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-zinc-500" />
            <CardTitle className="text-base">可用工具类别</CardTitle>
          </div>
          <CardDescription>
            Agent 可以使用的工具功能范围
          </CardDescription>
        </CardHeader>
        <CardContent>
          {agent.tool_categories && agent.tool_categories.length > 0 ? (
            <div className="space-y-2">
              {agent.tool_categories.map((cat) => {
                const info = getToolCategoryLabel(cat);
                const IconComponent = info.icon;
                return (
                  <div key={cat} className="flex items-center gap-3 p-2 rounded-lg bg-zinc-50 dark:bg-zinc-800/50">
                    <div className="flex items-center justify-center w-7 h-7 rounded-md bg-white dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300">
                      <IconComponent className="h-3.5 w-3.5" />
                    </div>
                    <div>
                      <span className="text-sm font-medium">{info.label}</span>
                      {info.desc && <p className="text-xs text-zinc-400">{info.desc}</p>}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-zinc-400">未限制工具类别，可使用所有工具</p>
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
