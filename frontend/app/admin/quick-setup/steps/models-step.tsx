"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Bot,
  Database,
  Server,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
  Clock,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { StepProps } from "@/types/quick-setup";
import {
  checkServicesHealth,
  getQuickStats,
  type HealthCheckResponse,
  type QuickStats,
} from "@/lib/api/quick-setup";

function ConfigDisplay({
  label,
  value,
  sensitive = false,
}: {
  label: string;
  value: string | number | null;
  sensitive?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <span className="text-sm text-zinc-500">{label}</span>
      <code className="text-sm bg-zinc-100 px-2 py-1 rounded dark:bg-zinc-800">
        {sensitive && value ? "••••••••" : value || "-"}
      </code>
    </div>
  );
}

interface TestProgress {
  phase: "idle" | "testing" | "done" | "error";
  currentService: string | null;
  testedServices: string[];
  error: string | null;
  startTime: number | null;
  endTime: number | null;
}

export function ModelsStep({ onComplete, onSkip, isLoading }: StepProps) {
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [testProgress, setTestProgress] = useState<TestProgress>({
    phase: "idle",
    currentService: null,
    testedServices: [],
    error: null,
    startTime: null,
    endTime: null,
  });

  const serviceNames = ["qdrant", "llm", "database"];
  const serviceLabels: Record<string, string> = {
    qdrant: "Qdrant 向量数据库",
    llm: "LLM API 服务",
    database: "SQLite 数据库",
  };

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        // 并行加载统计和健康检查，页面加载时直接显示结果
        const [statsData, healthData] = await Promise.all([
          getQuickStats(),
          checkServicesHealth(),
        ]);
        setStats(statsData);
        setHealth(healthData);
      } catch (e) {
        console.error("加载失败", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleTestConnection = useCallback(async () => {
    // 开始测试，显示进度动画
    setTestProgress({
      phase: "testing",
      currentService: null,
      testedServices: [],
      error: null,
      startTime: Date.now(),
      endTime: null,
    });

    try {
      // 逐步显示测试进度
      for (const service of serviceNames) {
        setTestProgress((prev) => ({
          ...prev,
          currentService: service,
        }));
        // 模拟步骤延迟，让用户看到进度
        await new Promise((resolve) => setTimeout(resolve, 300));
        setTestProgress((prev) => ({
          ...prev,
          testedServices: [...prev.testedServices, service],
        }));
      }

      // 调用实际 API
      const healthData = await checkServicesHealth();
      setHealth(healthData);

      setTestProgress((prev) => ({
        ...prev,
        phase: "done",
        currentService: null,
        endTime: Date.now(),
      }));
    } catch (e) {
      console.error("测试失败", e);
      setTestProgress((prev) => ({
        ...prev,
        phase: "error",
        currentService: null,
        error: e instanceof Error ? e.message : "测试连接失败",
        endTime: Date.now(),
      }));
    }
  }, []);

  const getTestDuration = () => {
    if (testProgress.startTime && testProgress.endTime) {
      return ((testProgress.endTime - testProgress.startTime) / 1000).toFixed(1);
    }
    return null;
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">模型 & 向量服务</h2>
        <p className="text-zinc-500">
          查看当前的 LLM、Embedding 和 Qdrant 配置。如需修改，请编辑{" "}
          <code className="bg-zinc-100 px-1 rounded dark:bg-zinc-800">.env</code>{" "}
          文件并重启服务。
        </p>
      </div>

      {/* Service Health */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Server className="h-4 w-4" />
              服务连接状态
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleTestConnection}
              disabled={testProgress.phase === "testing"}
            >
              {testProgress.phase === "testing" ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              {testProgress.phase === "testing" ? "测试中..." : "测试连接"}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* 测试进度显示 */}
          {testProgress.phase === "testing" && (
            <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="flex items-center gap-2 mb-3">
                <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                  正在测试服务连接...
                </span>
              </div>
              <div className="space-y-2">
                {serviceNames.map((service) => {
                  const isTested = testProgress.testedServices.includes(service);
                  const isCurrent = testProgress.currentService === service;
                  return (
                    <div
                      key={service}
                      className="flex items-center gap-2 text-sm"
                    >
                      {isTested ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : isCurrent ? (
                        <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                      ) : (
                        <Clock className="h-4 w-4 text-zinc-300" />
                      )}
                      <span
                        className={isTested ? "text-green-600" : isCurrent ? "text-blue-600" : "text-zinc-400"}
                      >
                        {serviceLabels[service]}
                      </span>
                      {isTested && <span className="text-green-500">✓</span>}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 测试错误 */}
          {testProgress.phase === "error" && (
            <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <span className="text-sm font-medium text-red-700 dark:text-red-300">
                  测试失败: {testProgress.error}
                </span>
              </div>
            </div>
          )}

          {/* 测试结果显示 */}
          {health && testProgress.phase === "done" && (
            <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium text-green-700 dark:text-green-300">
                    测试完成
                  </span>
                </div>
                {getTestDuration() && (
                  <span className="text-xs text-green-600">耗时 {getTestDuration()}s</span>
                )}
              </div>
              <div className="text-sm text-green-600">
                {health.all_ok
                  ? `✅ 所有 ${health.services.length} 个服务连接正常`
                  : `⚠️ ${health.services.filter((s) => s.status === "ok").length}/${health.services.length} 个服务正常`}
              </div>
            </div>
          )}

          {/* 服务详细状态 */}
          {health && testProgress.phase !== "testing" && (
            <div className="grid gap-3 md:grid-cols-3">
              {health.services.map((service) => (
                <div
                  key={service.name}
                  className="flex flex-col rounded-lg border p-3"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {service.status === "ok" ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="font-medium">{serviceLabels[service.name] || service.name}</span>
                    </div>
                    <Badge
                      variant={service.status === "ok" ? "default" : "destructive"}
                      className={
                        service.status === "ok" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" : ""
                      }
                    >
                      {service.status === "ok" ? "正常" : "异常"}
                    </Badge>
                  </div>
                  {service.message && (
                    <p className="text-xs text-zinc-500 mt-1">{service.message}</p>
                  )}
                  {service.latency_ms && (
                    <p className="text-xs text-zinc-400 mt-1">延迟: {service.latency_ms}ms</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {health && !health.all_ok && (
            <p className="mt-3 text-sm text-amber-600">
              部分服务连接异常，请检查配置和服务状态
            </p>
          )}
        </CardContent>
      </Card>

      {/* LLM Config */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="h-4 w-4" />
                LLM 配置
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ConfigDisplay label="Provider" value={stats.settings.llm_provider} />
              <ConfigDisplay label="Model" value={stats.settings.llm_model} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-4 w-4" />
                Embedding 配置
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ConfigDisplay label="Model" value={stats.settings.embedding_model} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Server className="h-4 w-4" />
                Qdrant 配置
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ConfigDisplay
                label="Collection"
                value={stats.settings.qdrant_collection}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <Database className="h-4 w-4" />
                其他配置
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm text-zinc-500">记忆系统</span>
                <Badge
                  variant={stats.settings.memory_enabled ? "default" : "secondary"}
                  className={
                    stats.settings.memory_enabled
                      ? "bg-green-100 text-green-700"
                      : ""
                  }
                >
                  {stats.settings.memory_enabled ? "启用" : "禁用"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-zinc-500">爬虫模块</span>
                <Badge
                  variant={stats.settings.crawler_enabled ? "default" : "secondary"}
                  className={
                    stats.settings.crawler_enabled
                      ? "bg-green-100 text-green-700"
                      : ""
                  }
                >
                  {stats.settings.crawler_enabled ? "启用" : "禁用"}
                </Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Help */}
      <Card className="bg-zinc-50 dark:bg-zinc-900">
        <CardContent className="pt-6">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            <strong>提示：</strong>模型配置通过环境变量管理，修改后需重启服务生效。
            详细说明请参考{" "}
            <code className="bg-zinc-200 px-1 rounded dark:bg-zinc-700">
              .env.example
            </code>{" "}
            文件。
          </p>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => onSkip()} disabled={isLoading}>
          跳过此步
        </Button>
        <Button
          onClick={() => onComplete()}
          disabled={isLoading || Boolean(health && !health.all_ok)}
        >
          {health && !health.all_ok ? "请先解决连接问题" : "确认并继续"}
        </Button>
      </div>
    </div>
  );
}
