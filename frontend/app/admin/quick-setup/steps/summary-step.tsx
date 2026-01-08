"use client";

import Link from "next/link";
import {
  CheckCircle,
  Circle,
  SkipForward,
  ExternalLink,
  MessageSquare,
  Database,
  Bot,
  Settings,
  RotateCcw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type StepProps } from "../page";

function StepStatus({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return (
        <Badge variant="default" className="bg-green-100 text-green-700">
          <CheckCircle className="mr-1 h-3 w-3" />
          已完成
        </Badge>
      );
    case "skipped":
      return (
        <Badge variant="secondary">
          <SkipForward className="mr-1 h-3 w-3" />
          已跳过
        </Badge>
      );
    case "in_progress":
      return (
        <Badge variant="outline" className="border-blue-300 text-blue-600">
          <Circle className="mr-1 h-3 w-3 fill-blue-500" />
          进行中
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-zinc-400">
          <Circle className="mr-1 h-3 w-3" />
          待完成
        </Badge>
      );
  }
}

export function SummaryStep({
  state,
  agentTypes,
  onComplete,
  onGoto,
  isLoading,
}: StepProps) {
  const completedCount = state.steps.filter((s) => s.status === "completed").length;
  const skippedCount = state.steps.filter((s) => s.status === "skipped").length;
  const totalSteps = state.steps.length;
  const progress = Math.round((completedCount / totalSteps) * 100);

  const selectedAgent = state.agent_id;
  const agentType = state.steps[3]?.data?.agent_type as string | undefined;
  const typeConfig = agentTypes.find((t) => t.type === agentType);

  const handleFinish = () => {
    onComplete({ finished: true });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">🎉 配置完成</h2>
        <p className="text-zinc-500">
          恭喜！您已完成 Quick Setup 向导。以下是配置摘要。
        </p>
      </div>

      {/* 进度概览 */}
      <Card className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-3xl font-bold text-green-600">{progress}%</div>
              <div className="text-sm text-zinc-500">配置完成度</div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-4">
                <div>
                  <div className="text-xl font-bold">{completedCount}</div>
                  <div className="text-xs text-zinc-500">已完成</div>
                </div>
                <div>
                  <div className="text-xl font-bold text-zinc-400">{skippedCount}</div>
                  <div className="text-xs text-zinc-500">已跳过</div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 步骤状态列表 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">步骤状态</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {state.steps.map((step) => (
              <div
                key={step.index}
                className="flex items-center justify-between py-2 border-b last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium">{step.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <StepStatus status={step.status} />
                  {step.status !== "completed" && step.index !== state.current_step && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs"
                      onClick={() => onGoto(step.index)}
                    >
                      前往
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 配置摘要 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">配置摘要</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {selectedAgent && (
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">当前 Agent</span>
              <Badge variant="outline">
                {typeConfig?.name || agentType || "未选择"}
              </Badge>
            </div>
          )}
          {Boolean(state.steps[4]?.data?.greeting_config) && (
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">开场白</span>
              <Badge
                variant="default"
                className="bg-green-100 text-green-700"
              >
                已启用
              </Badge>
            </div>
          )}
          {Boolean(state.steps[5]?.data?.web_enabled) && (
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">网页嵌入</span>
              <Badge
                variant="default"
                className="bg-green-100 text-green-700"
              >
                已启用
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 快捷入口 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">快捷入口</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            <Button variant="outline" className="justify-start" asChild>
              <Link href="/admin/agents">
                <Bot className="mr-2 h-4 w-4" />
                Agent 管理
                <ExternalLink className="ml-auto h-4 w-4" />
              </Link>
            </Button>
            {selectedAgent && (
              <Button variant="outline" className="justify-start" asChild>
                <Link href={`/admin/agents/${selectedAgent}/faq`}>
                  <MessageSquare className="mr-2 h-4 w-4" />
                  FAQ 管理
                  <ExternalLink className="ml-auto h-4 w-4" />
                </Link>
              </Button>
            )}
            {selectedAgent && (
              <Button variant="outline" className="justify-start" asChild>
                <Link href={`/admin/agents/${selectedAgent}/greeting`}>
                  <MessageSquare className="mr-2 h-4 w-4" />
                  开场白设置
                  <ExternalLink className="ml-auto h-4 w-4" />
                </Link>
              </Button>
            )}
            <Button variant="outline" className="justify-start" asChild>
              <Link href="/admin/knowledge">
                <Database className="mr-2 h-4 w-4" />
                知识库管理
                <ExternalLink className="ml-auto h-4 w-4" />
              </Link>
            </Button>
            <Button variant="outline" className="justify-start" asChild>
              <Link href="/admin/settings">
                <Settings className="mr-2 h-4 w-4" />
                设置中心
                <ExternalLink className="ml-auto h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 操作按钮 */}
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={() => onGoto(0)}
          disabled={isLoading}
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          重新运行向导
        </Button>
        <Button onClick={handleFinish} disabled={isLoading}>
          完成配置
          <CheckCircle className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
