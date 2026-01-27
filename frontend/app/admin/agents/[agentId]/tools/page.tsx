"use client";

import { useParams } from "next/navigation";
import { Wrench, Settings2, CheckCircle, XCircle, ChevronDown } from "lucide-react";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getToolCategoryLabel } from "@/lib/config/labels";
import { useState } from "react";
import { cn } from "@/lib/utils";

export default function AgentToolsPage() {
  const params = useParams();
  const agentId = params.agentId as string;
  const { agent } = useAgentDetail({ agentId });
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  if (!agent) return null;

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

  return (
    <div className="space-y-6">
      {/* 工具类别 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-zinc-500" />
            <CardTitle className="text-base">可用功能</CardTitle>
          </div>
          <CardDescription>
            Agent 可以使用的工具能力，点击展开查看具体工具
          </CardDescription>
        </CardHeader>
        <CardContent>
          {agent.tool_categories && agent.tool_categories.length > 0 ? (
            <div className="space-y-2">
              {agent.tool_categories.map((category) => {
                const info = getToolCategoryLabel(category);
                const IconComponent = info.icon;
                const isExpanded = expandedCategories.has(category);
                return (
                  <div
                    key={category}
                    className="rounded-lg border bg-zinc-50/50 dark:bg-zinc-800/30"
                  >
                    <button
                      type="button"
                      onClick={() => toggleCategory(category)}
                      className="flex w-full items-center justify-between p-3 text-left hover:bg-zinc-100 dark:hover:bg-zinc-800/50 rounded-lg transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-white dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300">
                          <IconComponent className="h-4 w-4" />
                        </div>
                        <div>
                          <span className="font-medium">{info.label}</span>
                          <p className="text-xs text-zinc-500">{info.desc}</p>
                        </div>
                      </div>
                      <ChevronDown
                        className={cn(
                          "h-4 w-4 text-zinc-400 transition-transform",
                          isExpanded && "rotate-180"
                        )}
                      />
                    </button>
                    {isExpanded && info.tools && info.tools.length > 0 && (
                      <div className="border-t px-3 py-2 space-y-1">
                        {info.tools.map((tool) => (
                          <div
                            key={tool.name}
                            className="flex items-center gap-2 py-1 pl-11 text-sm"
                          >
                            <span className="text-zinc-400">•</span>
                            <code className="text-xs bg-zinc-100 dark:bg-zinc-700 px-1.5 py-0.5 rounded">
                              {tool.name}
                            </code>
                            <span className="text-zinc-500">{tool.desc}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-zinc-500">未限制工具类别，可使用所有工具</p>
          )}
        </CardContent>
      </Card>

      {/* 工具策略 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings2 className="h-4 w-4 text-zinc-500" />
            <CardTitle className="text-base">调用策略</CardTitle>
          </div>
          <CardDescription>
            控制 Agent 如何使用工具来回答问题
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {agent.tool_policy ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="flex items-center gap-3">
                    {agent.tool_policy.allow_direct_answer ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-zinc-300" />
                    )}
                    <div>
                      <p className="font-medium">允许直接回答</p>
                      <p className="text-xs text-zinc-500">
                        {agent.tool_policy.allow_direct_answer
                          ? "可以不调用工具直接回复简单问题"
                          : "必须调用工具后才能回答"}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={agent.tool_policy.allow_direct_answer ? "default" : "secondary"}
                    className={
                      agent.tool_policy.allow_direct_answer
                        ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                        : ""
                    }
                  >
                    {agent.tool_policy.allow_direct_answer ? "开启" : "关闭"}
                  </Badge>
                </div>

                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="font-medium">最少调用次数</p>
                    <p className="text-xs text-zinc-500">
                      {agent.tool_policy.min_tool_calls === 0
                        ? "不限制，可以不调用工具"
                        : `每次对话至少调用 ${agent.tool_policy.min_tool_calls} 次工具`}
                    </p>
                  </div>
                  <Badge variant="outline" className="text-lg px-3">
                    {agent.tool_policy.min_tool_calls === 0
                      ? "不限"
                      : String(agent.tool_policy.min_tool_calls)}
                  </Badge>
                </div>
              </div>

              {agent.tool_policy.fallback_tool && (
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div>
                    <p className="font-medium">备选工具</p>
                    <p className="text-xs text-zinc-500">
                      当其他工具无法回答时，使用此工具兜底
                    </p>
                  </div>
                  <Badge variant="secondary">{String(agent.tool_policy.fallback_tool)}</Badge>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-zinc-500">使用默认工具策略</p>
          )}
        </CardContent>
      </Card>

      {/* 工具调用统计（占位） */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">工具调用统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-32 items-center justify-center rounded-lg bg-zinc-50 dark:bg-zinc-900">
            <p className="text-sm text-zinc-400">统计数据开发中...</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
