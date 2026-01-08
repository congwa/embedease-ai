"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  Database,
  Server,
  CheckCircle,
  XCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type StepProps } from "../page";
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

export function ModelsStep({ onComplete, onSkip, isLoading }: StepProps) {
  const [stats, setStats] = useState<QuickStats | null>(null);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
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

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      const healthData = await checkServicesHealth();
      setHealth(healthData);
    } catch (e) {
      console.error("测试失败", e);
    } finally {
      setTesting(false);
    }
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
      {health && (
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
                disabled={testing}
              >
                {testing ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                测试连接
              </Button>
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
                    {service.status === "ok" ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                    <span className="font-medium capitalize">{service.name}</span>
                  </div>
                  <Badge
                    variant={service.status === "ok" ? "default" : "destructive"}
                    className={
                      service.status === "ok" ? "bg-green-100 text-green-700" : ""
                    }
                  >
                    {service.status === "ok" ? "正常" : "异常"}
                  </Badge>
                </div>
              ))}
            </div>
            {!health.all_ok && (
              <p className="mt-3 text-sm text-amber-600">
                部分服务连接异常，请检查配置和服务状态
              </p>
            )}
          </CardContent>
        </Card>
      )}

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
