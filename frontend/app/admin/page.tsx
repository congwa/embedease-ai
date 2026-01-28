"use client";

import { useEffect, useState } from "react";
import {
  Package,
  MessageSquare,
  Users,
  Globe,
  Bot,
  Clock,
  Headphones,
  TrendingUp,
  Network,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageHeader, StatCard } from "@/components/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getDashboardStats, getSupervisorGlobalConfig, type DashboardStats, type SupervisorGlobalConfig } from "@/lib/api/admin";
import { Badge } from "@/components/ui/badge";
import { useModeStore } from "@/stores";

export default function AdminDashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [supervisorConfig, setSupervisorConfig] = useState<SupervisorGlobalConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { mode, fetchModeState } = useModeStore();

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [statsData, supervisorData] = await Promise.all([
          getDashboardStats(),
          getSupervisorGlobalConfig(),
          fetchModeState(),
        ]);
        setStats(statsData);
        setSupervisorConfig(supervisorData);
      } catch (e) {
        setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [fetchModeState]);

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-600 dark:bg-red-900/20 dark:text-red-400">
        {error}
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="仪表盘"
        description="系统数据概览"
      />

      {/* 运行模式状态 */}
      <Card className={mode === "supervisor" ? "border-violet-200 bg-violet-50/50 dark:border-violet-800 dark:bg-violet-950/30" : "border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-950/30"}>
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex items-center gap-4">
            <div className={`flex h-12 w-12 items-center justify-center rounded-full ${mode === "supervisor" ? "bg-violet-100 dark:bg-violet-900/50" : "bg-emerald-100 dark:bg-emerald-900/50"}`}>
              {mode === "supervisor" ? (
                <Network className="h-6 w-6 text-violet-600 dark:text-violet-400" />
              ) : (
                <Bot className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold">
                  {mode === "supervisor" ? "Supervisor 模式" : "单 Agent 模式"}
                </span>
                <Badge variant="secondary" className={mode === "supervisor" ? "bg-violet-100 text-violet-700 dark:bg-violet-900 dark:text-violet-300" : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300"}>
                  运行中
                </Badge>
              </div>
              <p className="text-sm text-zinc-500">
                {mode === "supervisor" 
                  ? "多个 Agent 协作，由 Supervisor 智能路由用户请求"
                  : "单个 Agent 处理所有用户请求"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => router.push("/admin/settings/mode")}>
              切换模式
            </Button>
            <Button size="sm" onClick={() => router.push("/admin/workspace")}>
              进入工作空间
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 核心指标 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="商品总数"
          value={stats.total_products.toLocaleString()}
          icon={Package}
        />
        <StatCard
          title="会话总数"
          value={stats.total_conversations.toLocaleString()}
          icon={MessageSquare}
          description={`今日 +${stats.today_conversations}`}
        />
        <StatCard
          title="用户总数"
          value={stats.total_users.toLocaleString()}
          icon={Users}
        />
        <StatCard
          title="消息总数"
          value={stats.total_messages.toLocaleString()}
          icon={TrendingUp}
          description={`今日 +${stats.today_messages}`}
        />
      </div>

      {/* Agent 概览与多Agent编排 */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Agent 概览 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Bot className="h-4 w-4" />
              Agent 概览
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stats.agent_stats?.total_agents || 0}
                </p>
                <p className="text-xs text-zinc-500">总数</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">
                  {stats.agent_stats?.enabled_agents || 0}
                </p>
                <p className="text-xs text-zinc-500">已启用</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-orange-500">
                  {supervisorConfig?.sub_agents?.length || 0}
                </p>
                <p className="text-xs text-zinc-500">子 Agent</p>
              </div>
            </div>
            {stats.agent_stats?.default_agent_name && (
              <div className="mt-4 pt-4 border-t">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-zinc-500">默认 Agent</span>
                  <Link 
                    href={`/admin/agents/${stats.agent_stats.default_agent_id}`}
                    className="flex items-center gap-1 text-primary hover:underline"
                  >
                    {stats.agent_stats.default_agent_name}
                    <ChevronRight className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 多Agent编排 */}
        <Card className={supervisorConfig?.enabled ? "border-orange-200 bg-orange-50/30 dark:border-orange-900 dark:bg-orange-950/20" : ""}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Network className={`h-4 w-4 ${supervisorConfig?.enabled ? "text-orange-500" : ""}`} />
                多Agent编排
              </CardTitle>
              <Badge variant={supervisorConfig?.enabled ? "default" : "secondary"}>
                {supervisorConfig?.enabled ? "全局已启用" : "全局已禁用"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            {!supervisorConfig?.enabled ? (
              <div className="space-y-3">
                <p className="text-sm text-zinc-500">
                  Supervisor 功能已禁用
                </p>
                <p className="text-xs text-zinc-400">
                  在 Supervisor 配置页面中启用
                </p>
                <Link 
                  href="/admin/settings/supervisor"
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  查看配置
                  <ChevronRight className="h-3 w-3" />
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-500/10 px-2 py-1 text-xs font-medium text-green-600 dark:text-green-400">
                    <Network className="h-3 w-3" />
                    Supervisor 已启用
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-zinc-500">子 Agent 数量</p>
                    <p className="text-lg font-semibold">{supervisorConfig.sub_agents.length}</p>
                  </div>
                  <div>
                    <p className="text-xs text-zinc-500">默认 Agent</p>
                    <p className="text-sm font-medium truncate">{stats.agent_stats?.default_agent_name || "未设置"}</p>
                  </div>
                </div>
                <Link 
                  href="/admin/settings/supervisor"
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  管理编排配置
                  <ChevronRight className="h-3 w-3" />
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 爬虫与会话状态 */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* 爬虫统计 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Globe className="h-4 w-4" />
              爬虫统计
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stats.total_crawl_sites}
                </p>
                <p className="text-xs text-zinc-500">站点数</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stats.total_crawl_tasks}
                </p>
                <p className="text-xs text-zinc-500">任务数</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-green-600">
                  {stats.crawl_success_rate}%
                </p>
                <p className="text-xs text-zinc-500">成功率</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 会话状态分布 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <MessageSquare className="h-4 w-4" />
              会话状态分布
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <Bot className="h-5 w-5 text-blue-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stats.ai_conversations}
                </p>
                <p className="text-xs text-zinc-500">AI 模式</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-yellow-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stats.pending_conversations}
                </p>
                <p className="text-xs text-zinc-500">等待接入</p>
              </div>
              <div className="text-center">
                <div className="mb-2 flex items-center justify-center">
                  <Headphones className="h-5 w-5 text-green-500" />
                </div>
                <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
                  {stats.human_conversations}
                </p>
                <p className="text-xs text-zinc-500">人工服务</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
