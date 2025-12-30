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
} from "lucide-react";
import { PageHeader, StatCard } from "@/components/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboardStats, type DashboardStats } from "@/lib/api/admin";

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        setIsLoading(true);
        const data = await getDashboardStats();
        setStats(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    }
    loadStats();
  }, []);

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
