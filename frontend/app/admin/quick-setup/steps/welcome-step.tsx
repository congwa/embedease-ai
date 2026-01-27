"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Server,
  Database,
  Bot,
  Loader2,
  ExternalLink,
  HelpCircle,
  Cpu,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type StepProps } from "../page";
import {
  getChecklist,
  getQuickStats,
  checkServicesHealth,
  type ChecklistResponse,
  type QuickStats,
  type HealthCheckResponse,
} from "@/lib/api/quick-setup";

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "ok":
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case "default":
      return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    case "missing":
    case "error":
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <AlertTriangle className="h-4 w-4 text-zinc-400" />;
  }
}

function CategoryCard({
  title,
  icon: Icon,
  items,
  onGotoStep,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  items: Array<{
    key: string;
    label: string;
    status: string;
    current_value: string | null;
    step_index: number | null;
  }>;
  onGotoStep: (index: number) => void;
}) {
  const okCount = items.filter((i) => i.status === "ok").length;
  const total = items.length;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Icon className="h-4 w-4" />
            {title}
          </span>
          <Badge
            variant={okCount === total ? "default" : "secondary"}
            className={okCount === total ? "bg-green-100 text-green-700" : ""}
          >
            {okCount}/{total}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.map((item) => (
          <div
            key={item.key}
            className="flex items-center justify-between py-1.5 text-sm"
          >
            <div className="flex items-center gap-2">
              <StatusIcon status={item.status} />
              <span>{item.label}</span>
            </div>
            <div className="flex items-center gap-2">
              {item.current_value && (
                <code className="text-xs text-zinc-500 bg-zinc-100 px-1.5 py-0.5 rounded dark:bg-zinc-800">
                  {item.current_value}
                </code>
              )}
              {item.step_index !== null && item.status !== "ok" && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => onGotoStep(item.step_index!)}
                >
                  配置
                </Button>
              )}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export function WelcomeStep({ state, onComplete, onGoto, isLoading }: StepProps) {
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [checklistData, statsData, healthData] = await Promise.all([
          getChecklist(),
          getQuickStats(),
          checkServicesHealth(),
        ]);
        setChecklist(checklistData);
        setStats(statsData);
        setHealth(healthData);
      } catch (e) {
        console.error("加载检查清单失败", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleGotoStep = (index: number) => {
    onGoto(index);
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  const groupedItems = checklist?.items.reduce(
    (acc, item) => {
      if (!acc[item.category]) acc[item.category] = [];
      acc[item.category].push(item);
      return acc;
    },
    {} as Record<string, typeof checklist.items>
  );

  const categoryConfig: Record<
    string,
    { title: string; icon: React.ComponentType<{ className?: string }> }
  > = {
    llm: { title: "LLM 配置", icon: Bot },
    embedding: { title: "Embedding 配置", icon: Database },
    qdrant: { title: "Qdrant 配置", icon: Server },
    rerank: { title: "Rerank 配置", icon: Server },
    memory: { title: "记忆系统", icon: Database },
    middleware: { title: "中间件配置", icon: Server },
    crawler: { title: "爬虫模块", icon: Server },
    support: { title: "客服支持", icon: Server },
  };

  return (
    <div className="space-y-6">
      {/* Welcome Message */}
      <div className="rounded-lg border bg-gradient-to-r from-blue-50 to-indigo-50 p-6 dark:from-blue-900/20 dark:to-indigo-900/20">
        <h2 className="text-xl font-semibold mb-2">👋 欢迎使用 Quick Setup</h2>
        <p className="text-zinc-600 dark:text-zinc-400">
          这个向导将帮助您一步步完成系统配置。下面是当前配置状态的概览，
          您可以点击各项直接跳转到对应的配置步骤。
        </p>
      </div>

      {/* Stats Overview - 精致的状态卡片 */}
      {stats && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Agent 数量 */}
          <div className="group relative overflow-hidden rounded-xl border border-zinc-200/60 bg-gradient-to-br from-white to-zinc-50/50 p-4 transition-all hover:border-zinc-300 hover:shadow-sm dark:border-zinc-800 dark:from-zinc-900 dark:to-zinc-900/50">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  Agent
                </p>
                <p className="text-3xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
                  {stats.agents.total}
                </p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
                <Bot className="h-4 w-4" />
              </div>
            </div>
            {stats.agents.default_name && (
              <p className="mt-2 truncate text-xs text-zinc-500" title={stats.agents.default_name}>
                默认: {stats.agents.default_name}
              </p>
            )}
          </div>

          {/* FAQ 条目 */}
          <div className="group relative overflow-hidden rounded-xl border border-zinc-200/60 bg-gradient-to-br from-white to-zinc-50/50 p-4 transition-all hover:border-zinc-300 hover:shadow-sm dark:border-zinc-800 dark:from-zinc-900 dark:to-zinc-900/50">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  FAQ
                </p>
                <p className="text-3xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
                  {stats.faq.total}
                </p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400">
                <HelpCircle className="h-4 w-4" />
              </div>
            </div>
            {stats.faq.unindexed > 0 && (
              <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                {stats.faq.unindexed} 条待索引
              </p>
            )}
          </div>

          {/* 知识源配置 */}
          <div className="group relative overflow-hidden rounded-xl border border-zinc-200/60 bg-gradient-to-br from-white to-zinc-50/50 p-4 transition-all hover:border-zinc-300 hover:shadow-sm dark:border-zinc-800 dark:from-zinc-900 dark:to-zinc-900/50">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  知识源
                </p>
                <p className="text-3xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
                  {stats.knowledge_configs.total}
                </p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400">
                <Database className="h-4 w-4" />
              </div>
            </div>
          </div>

          {/* 当前模型 */}
          <div className="group relative overflow-hidden rounded-xl border border-zinc-200/60 bg-gradient-to-br from-white to-zinc-50/50 p-4 transition-all hover:border-zinc-300 hover:shadow-sm dark:border-zinc-800 dark:from-zinc-900 dark:to-zinc-900/50">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-xs font-medium uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  模型
                </p>
                <p 
                  className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-100" 
                  title={stats.settings.llm_model}
                >
                  {stats.settings.llm_model?.split('/').pop() || stats.settings.llm_model}
                </p>
              </div>
              <div className="ml-2 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-500/10 text-orange-600 dark:bg-orange-500/20 dark:text-orange-400">
                <Cpu className="h-4 w-4" />
              </div>
            </div>
            {stats.settings.llm_model?.includes('/') && (
              <p className="mt-2 truncate text-xs text-zinc-400" title={stats.settings.llm_model}>
                {stats.settings.llm_model.split('/')[0]}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Health Status */}
      {health && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Server className="h-4 w-4" />
              服务状态
              <Badge
                variant={health.all_ok ? "default" : "destructive"}
                className={health.all_ok ? "bg-green-100 text-green-700" : ""}
              >
                {health.all_ok ? "全部正常" : "部分异常"}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-3">
              {health.services.map((service) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-2">
                    <StatusIcon status={service.status} />
                    <span className="font-medium capitalize">{service.name}</span>
                  </div>
                  <div className="text-xs text-zinc-500">
                    {service.latency_ms
                      ? `${service.latency_ms.toFixed(0)}ms`
                      : service.message}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Checklist Summary */}
      {checklist && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-base">
              <span>配置检查清单</span>
              <div className="flex items-center gap-2 text-sm font-normal">
                <Badge variant="default" className="bg-green-100 text-green-700">
                  {checklist.ok_count} 已配置
                </Badge>
                {checklist.default_count > 0 && (
                  <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                    {checklist.default_count} 默认值
                  </Badge>
                )}
                {checklist.missing_count > 0 && (
                  <Badge variant="destructive">
                    {checklist.missing_count} 缺失
                  </Badge>
                )}
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              {groupedItems &&
                Object.entries(groupedItems).map(([category, items]) => {
                  const config = categoryConfig[category];
                  if (!config) return null;
                  return (
                    <CategoryCard
                      key={category}
                      title={config.title}
                      icon={config.icon}
                      items={items}
                      onGotoStep={handleGotoStep}
                    />
                  );
                })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action */}
      <div className="flex justify-end">
        <Button onClick={() => onComplete()} disabled={isLoading}>
          开始配置
          <ExternalLink className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
