"use client";

import { Settings2, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface ToolPolicy {
  allow_direct_answer?: boolean;
  min_tool_calls?: number;
  fallback_tool?: string | null;
  clarification_tool?: string | null;
}

export interface ToolPolicyDisplayProps {
  policy: ToolPolicy | Record<string, unknown> | null;
  title?: string;
  description?: string;
  showFullDetails?: boolean;
}

export function ToolPolicyDisplay({
  policy,
  title = "调用策略",
  description = "控制 Agent 如何使用工具来回答问题",
  showFullDetails = true,
}: ToolPolicyDisplayProps) {
  const typedPolicy = policy as ToolPolicy | null;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-zinc-500" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        {typedPolicy ? (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="flex items-center gap-3">
                  {typedPolicy.allow_direct_answer ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-zinc-300" />
                  )}
                  <div>
                    <p className="font-medium">允许直接回答</p>
                    {showFullDetails && (
                      <p className="text-xs text-zinc-500">
                        {typedPolicy.allow_direct_answer
                          ? "可以不调用工具直接回复简单问题"
                          : "必须调用工具后才能回答"}
                      </p>
                    )}
                  </div>
                </div>
                <Badge
                  variant={typedPolicy.allow_direct_answer ? "default" : "secondary"}
                  className={
                    typedPolicy.allow_direct_answer
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : ""
                  }
                >
                  {typedPolicy.allow_direct_answer ? "开启" : "关闭"}
                </Badge>
              </div>

              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="font-medium">最少调用次数</p>
                  {showFullDetails && (
                    <p className="text-xs text-zinc-500">
                      {typedPolicy.min_tool_calls === 0
                        ? "不限制，可以不调用工具"
                        : `每次对话至少调用 ${typedPolicy.min_tool_calls} 次工具`}
                    </p>
                  )}
                </div>
                <Badge variant="outline" className="text-lg px-3">
                  {typedPolicy.min_tool_calls === 0
                    ? "不限"
                    : String(typedPolicy.min_tool_calls)}
                </Badge>
              </div>
            </div>

            {showFullDetails && typedPolicy.fallback_tool && (
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="font-medium">备选工具</p>
                  <p className="text-xs text-zinc-500">
                    当其他工具无法回答时，使用此工具兜底
                  </p>
                </div>
                <Badge variant="secondary">{String(typedPolicy.fallback_tool)}</Badge>
              </div>
            )}

            {showFullDetails && typedPolicy.clarification_tool && (
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="font-medium">澄清工具</p>
                  <p className="text-xs text-zinc-500">
                    信息不足时用于引导用户明确需求
                  </p>
                </div>
                <Badge variant="secondary">{String(typedPolicy.clarification_tool)}</Badge>
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-zinc-500">使用默认工具策略</p>
        )}
      </CardContent>
    </Card>
  );
}
