"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Network, Check, ArrowRight, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useModeStore, useAgentStore } from "@/stores";
import { PageHeader } from "@/components/admin";
import { cn } from "@/lib/utils";

export default function ModeSettingsPage() {
  const router = useRouter();
  const { mode, switchMode, fetchModeState, isLoading } = useModeStore();
  const { agents, fetchAgents } = useAgentStore();
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [targetMode, setTargetMode] = useState<"single" | "supervisor" | null>(null);

  useEffect(() => {
    fetchModeState();
    fetchAgents();
  }, [fetchModeState, fetchAgents]);

  const handleModeSelect = (selectedMode: "single" | "supervisor") => {
    if (selectedMode === mode) return;
    setTargetMode(selectedMode);
    setShowConfirmDialog(true);
  };

  const handleConfirmSwitch = async () => {
    if (!targetMode) return;
    const success = await switchMode(targetMode);
    setShowConfirmDialog(false);
    if (success) {
      router.push("/admin/workspace");
    }
  };

  const enabledAgents = agents.filter(a => a.status === "enabled");

  return (
    <div className="space-y-6">
      <PageHeader
        title="运行模式设置"
        description="选择系统的运行模式，决定 Agent 的工作方式"
      />

      {/* 当前模式状态 */}
      <Card>
        <CardHeader>
          <CardTitle>当前模式</CardTitle>
          <CardDescription>
            系统当前正在以下模式运行
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            {mode === "supervisor" ? (
              <>
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-900/30">
                  <Network className="h-6 w-6 text-violet-600 dark:text-violet-400" />
                </div>
                <div>
                  <div className="text-lg font-semibold">Supervisor 模式</div>
                  <div className="text-sm text-zinc-500">
                    多个 Agent 协作，由 Supervisor 智能路由用户请求
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                  <Bot className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <div className="text-lg font-semibold">单 Agent 模式</div>
                  <div className="text-sm text-zinc-500">
                    单个 Agent 处理所有用户请求
                  </div>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 模式选择 */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* 单 Agent 模式 */}
        <Card
          className={cn(
            "cursor-pointer transition-all",
            mode === "single"
              ? "border-emerald-500 ring-2 ring-emerald-500/20"
              : "hover:border-zinc-300 dark:hover:border-zinc-600"
          )}
          onClick={() => handleModeSelect("single")}
        >
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                <Bot className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              </div>
              {mode === "single" && (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500">
                  <Check className="h-4 w-4 text-white" />
                </div>
              )}
            </div>
            <CardTitle className="mt-4">单 Agent 模式</CardTitle>
            <CardDescription>
              一个 Agent 处理所有用户请求，配置简单，适合单一业务场景
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="text-sm font-medium">适用场景：</div>
              <ul className="space-y-2 text-sm text-zinc-500">
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-500" />
                  单一业务场景
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-500" />
                  快速上线需求
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-500" />
                  简单配置管理
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Supervisor 模式 */}
        <Card
          className={cn(
            "cursor-pointer transition-all",
            mode === "supervisor"
              ? "border-violet-500 ring-2 ring-violet-500/20"
              : "hover:border-zinc-300 dark:hover:border-zinc-600"
          )}
          onClick={() => handleModeSelect("supervisor")}
        >
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-900/30">
                <Network className="h-6 w-6 text-violet-600 dark:text-violet-400" />
              </div>
              {mode === "supervisor" && (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-violet-500">
                  <Check className="h-4 w-4 text-white" />
                </div>
              )}
            </div>
            <CardTitle className="mt-4">Supervisor 模式</CardTitle>
            <CardDescription>
              多个 Agent 协作，由 Supervisor 智能路由请求到最合适的子 Agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="text-sm font-medium">适用场景：</div>
              <ul className="space-y-2 text-sm text-zinc-500">
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-violet-500" />
                  多业务线并行
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-violet-500" />
                  专业领域分工
                </li>
                <li className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-violet-500" />
                  复杂对话场景
                </li>
              </ul>
              {enabledAgents.length > 0 && (
                <div className="mt-4 rounded-lg bg-zinc-50 p-3 dark:bg-zinc-800/50">
                  <div className="text-xs font-medium text-zinc-500">
                    可用子 Agent: {enabledAgents.length} 个
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {enabledAgents.slice(0, 3).map(agent => (
                      <span
                        key={agent.id}
                        className="rounded bg-zinc-200 px-2 py-0.5 text-xs dark:bg-zinc-700"
                      >
                        {agent.name}
                      </span>
                    ))}
                    {enabledAgents.length > 3 && (
                      <span className="text-xs text-zinc-400">
                        +{enabledAgents.length - 3} 更多
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 快捷操作 */}
      <Card>
        <CardContent className="flex items-center justify-between p-4">
          <div>
            <div className="font-medium">进入工作空间</div>
            <div className="text-sm text-zinc-500">
              在工作空间中配置和管理 {mode === "supervisor" ? "Supervisor 编排" : "Agent"}
            </div>
          </div>
          <Button onClick={() => router.push("/admin/workspace")}>
            进入工作空间
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </CardContent>
      </Card>

      {/* 模式切换确认对话框 */}
      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              确认切换模式
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <p>
                  您即将从{" "}
                  <span className="font-medium">
                    {mode === "single" ? "单 Agent 模式" : "Supervisor 模式"}
                  </span>{" "}
                  切换到{" "}
                  <span className="font-medium">
                    {targetMode === "single" ? "单 Agent 模式" : "Supervisor 模式"}
                  </span>
                </p>

                {targetMode === "supervisor" && (
                  <div className="rounded-lg bg-violet-50 p-3 dark:bg-violet-900/20">
                    <div className="font-medium text-violet-900 dark:text-violet-100">
                      切换到 Supervisor 模式后：
                    </div>
                    <ul className="mt-2 space-y-1 text-sm text-violet-700 dark:text-violet-300">
                      <li>• 当前 Agent 将成为 Supervisor 的默认子 Agent</li>
                      <li>• 您可以添加更多子 Agent 进行协作</li>
                      <li>• 用户请求将由 Supervisor 智能路由</li>
                    </ul>
                  </div>
                )}

                {targetMode === "single" && (
                  <div className="rounded-lg bg-emerald-50 p-3 dark:bg-emerald-900/20">
                    <div className="font-medium text-emerald-900 dark:text-emerald-100">
                      切换到单 Agent 模式后：
                    </div>
                    <ul className="mt-2 space-y-1 text-sm text-emerald-700 dark:text-emerald-300">
                      <li>• Supervisor 编排将被禁用</li>
                      <li>• 所有请求将由默认 Agent 处理</li>
                      <li>• 其他 Agent 配置将被保留</li>
                    </ul>
                  </div>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmSwitch} disabled={isLoading}>
              {isLoading ? "切换中..." : "确认切换"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
