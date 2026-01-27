"use client";

import { useEffect, useState } from "react";
import {
  Settings,
  Server,
  Database,
  Brain,
  Bot,
  Layers,
  RefreshCw,
  Eye,
  EyeOff,
  Check,
  X,
  ChevronRight,
  Pencil,
} from "lucide-react";
import { PageHeader } from "@/components/admin";
import { getAgentTypeLabel } from "@/lib/config/labels";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getSettingsOverview,
  getMiddlewareDefaults,
  getRawConfig,
  getAgents,
  type SettingsOverview,
  type MiddlewareDefaults,
  type Agent,
} from "@/lib/api/agents";

function StatusBadge({ enabled }: { enabled: boolean }) {
  return enabled ? (
    <Badge variant="default" className="bg-green-100 text-green-700 hover:bg-green-100">
      <Check className="mr-1 h-3 w-3" />
      启用
    </Badge>
  ) : (
    <Badge variant="secondary" className="bg-zinc-100 text-zinc-500">
      <X className="mr-1 h-3 w-3" />
      禁用
    </Badge>
  );
}

function ConfigItem({
  label,
  value,
  sensitive = false,
}: {
  label: string;
  value: string | number | null | undefined;
  sensitive?: boolean;
}) {
  const [visible, setVisible] = useState(!sensitive);

  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-zinc-500">{label}</span>
      <div className="flex items-center gap-2">
        <code className="rounded bg-zinc-100 px-2 py-1 text-sm dark:bg-zinc-800">
          {sensitive && !visible ? "••••••••" : value ?? "-"}
        </code>
        {sensitive && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setVisible(!visible)}
          >
            {visible ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
          </Button>
        )}
      </div>
    </div>
  );
}

function MiddlewareCompareRow({
  label,
  globalValue,
  agentValue,
}: {
  label: string;
  globalValue: boolean;
  agentValue: boolean | null | undefined;
}) {
  const normalizedAgentValue = agentValue ?? undefined;
  const isOverridden = normalizedAgentValue !== undefined && normalizedAgentValue !== globalValue;
  const effectiveValue = agentValue ?? globalValue;

  return (
    <TableRow>
      <TableCell className="font-medium">{label}</TableCell>
      <TableCell>
        <StatusBadge enabled={globalValue} />
      </TableCell>
      <TableCell>
        {isOverridden ? (
          <Badge variant="outline" className="border-amber-300 text-amber-600">
            已覆盖
          </Badge>
        ) : (
          <Badge variant="outline" className="text-zinc-400">
            继承
          </Badge>
        )}
      </TableCell>
      <TableCell>
        <StatusBadge enabled={effectiveValue} />
      </TableCell>
    </TableRow>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsOverview | null>(null);
  const [middlewareDefaults, setMiddlewareDefaults] = useState<MiddlewareDefaults | null>(null);
  const [rawConfig, setRawConfig] = useState<Record<string, unknown> | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRawConfig, setShowRawConfig] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [settingsData, middlewareData, agentsData] = await Promise.all([
        getSettingsOverview(),
        getMiddlewareDefaults(),
        getAgents({ limit: 100 }),
      ]);
      setSettings(settingsData);
      setMiddlewareDefaults(middlewareData);
      setAgents(agentsData.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  };

  const loadRawConfig = async () => {
    if (!showRawConfig && !rawConfig) {
      const data = await getRawConfig();
      setRawConfig(data);
    }
    setShowRawConfig(!showRawConfig);
  };

  useEffect(() => {
    loadData();
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
      <div className="space-y-4">
        <PageHeader title="设置中心" description="系统配置与中间件管理" />
        <div className="rounded-lg bg-red-50 p-4 text-red-600 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (!settings || !middlewareDefaults) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="设置中心" description="系统配置与中间件管理" />
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {/* 全局概览卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* LLM 配置 */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Bot className="h-4 w-4" />
                LLM 配置
              </CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <a href="/admin/settings/llm-config">
                  <Pencil className="mr-1 h-3 w-3" />
                  配置
                </a>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-1">
            <ConfigItem label="Provider" value={settings.llm_provider} />
            <ConfigItem label="Model" value={settings.llm_model} />
            <ConfigItem label="Base URL" value={settings.llm_base_url} />
            <ConfigItem label="API Key" value={settings.llm_api_key_masked} sensitive />
          </CardContent>
        </Card>

        {/* Embedding 配置 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Layers className="h-4 w-4" />
              Embedding 配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <ConfigItem label="Provider" value={settings.embedding_provider} />
            <ConfigItem label="Model" value={settings.embedding_model} />
            <ConfigItem label="Dimension" value={settings.embedding_dimension} />
          </CardContent>
        </Card>

        {/* Rerank 配置 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Server className="h-4 w-4" />
              Rerank 配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">状态</span>
              <StatusBadge enabled={settings.rerank_enabled} />
            </div>
            {settings.rerank_enabled && (
              <>
                <ConfigItem label="Provider" value={settings.rerank_provider} />
                <ConfigItem label="Model" value={settings.rerank_model} />
              </>
            )}
          </CardContent>
        </Card>

        {/* Memory 配置 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" />
              Memory 配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">总开关</span>
              <StatusBadge enabled={settings.memory_enabled} />
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">Store</span>
              <StatusBadge enabled={settings.memory_store_enabled} />
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">Fact</span>
              <StatusBadge enabled={settings.memory_fact_enabled} />
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">Graph</span>
              <StatusBadge enabled={settings.memory_graph_enabled} />
            </div>
          </CardContent>
        </Card>

        {/* Qdrant 配置 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4" />
              Qdrant 配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <ConfigItem label="Host" value={settings.qdrant_host} />
            <ConfigItem label="Port" value={settings.qdrant_port} />
            <ConfigItem label="Collection" value={settings.qdrant_collection} />
          </CardContent>
        </Card>

        {/* 其他配置 */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Settings className="h-4 w-4" />
              其他配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">Crawler</span>
              <StatusBadge enabled={settings.crawler_enabled} />
            </div>
            <ConfigItem label="数据库路径" value={settings.database_path} />
          </CardContent>
        </Card>

        {/* 存储配置 (MinIO) */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Database className="h-4 w-4" />
              图片存储 (MinIO)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-zinc-500">状态</span>
              <StatusBadge enabled={settings.minio_enabled} />
            </div>
            {settings.minio_enabled && (
              <>
                <ConfigItem label="Endpoint" value={settings.minio_endpoint} />
                <ConfigItem label="Bucket" value={settings.minio_bucket} />
                <ConfigItem label="图片大小限制" value={`${settings.image_max_size_mb} MB`} />
                <ConfigItem label="单消息图片数" value={settings.image_max_count} />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* 中间件默认配置 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">全局中间件默认配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border p-4">
              <div className="mb-2 text-sm font-medium">TODO 规划</div>
              <StatusBadge enabled={middlewareDefaults.todo_enabled} />
            </div>
            <div className="rounded-lg border p-4">
              <div className="mb-2 text-sm font-medium">工具限制</div>
              <StatusBadge enabled={middlewareDefaults.tool_limit_enabled} />
              {middlewareDefaults.tool_limit_enabled && (
                <div className="mt-2 text-xs text-zinc-500">
                  单次限制: {middlewareDefaults.tool_limit_run ?? "无限制"}
                </div>
              )}
            </div>
            <div className="rounded-lg border p-4">
              <div className="mb-2 text-sm font-medium">工具重试</div>
              <StatusBadge enabled={middlewareDefaults.tool_retry_enabled} />
              {middlewareDefaults.tool_retry_enabled && (
                <div className="mt-2 text-xs text-zinc-500">
                  最大重试: {middlewareDefaults.tool_retry_max_retries}
                </div>
              )}
            </div>
            <div className="rounded-lg border p-4">
              <div className="mb-2 text-sm font-medium">上下文压缩</div>
              <StatusBadge enabled={middlewareDefaults.summarization_enabled} />
              {middlewareDefaults.summarization_enabled && (
                <div className="mt-2 text-xs text-zinc-500">
                  触发阈值: {middlewareDefaults.summarization_trigger_messages} 条
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent Middleware 对比 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agent 中间件配置对比</CardTitle>
          <p className="text-sm text-zinc-500">点击展开查看各 Agent 的中间件配置详情</p>
        </CardHeader>
        <CardContent>
          <Accordion className="w-full space-y-2">
            {agents.map((agent) => (
              <AccordionItem
                key={agent.id}
                value={agent.id}
                className="border rounded-lg px-4 data-[state=open]:bg-zinc-50 dark:data-[state=open]:bg-zinc-800/50"
              >
                <AccordionTrigger className="hover:no-underline py-4">
                  <div className="flex items-center gap-3">
                    <Bot className="h-4 w-4 text-zinc-500" />
                    <span className="font-medium">{agent.name}</span>
                    <Badge variant="outline">{getAgentTypeLabel(agent.type)}</Badge>
                    {agent.is_default && (
                      <Badge className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-xs">
                        当前激活
                      </Badge>
                    )}
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>中间件</TableHead>
                        <TableHead>全局默认</TableHead>
                        <TableHead>覆盖状态</TableHead>
                        <TableHead>生效值</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <MiddlewareCompareRow
                        label="TODO 规划"
                        globalValue={middlewareDefaults.todo_enabled}
                        agentValue={agent.middleware_flags?.todo_enabled}
                      />
                      <MiddlewareCompareRow
                        label="上下文压缩"
                        globalValue={middlewareDefaults.summarization_enabled}
                        agentValue={agent.middleware_flags?.summarization_enabled}
                      />
                      <MiddlewareCompareRow
                        label="工具重试"
                        globalValue={middlewareDefaults.tool_retry_enabled}
                        agentValue={agent.middleware_flags?.tool_retry_enabled}
                      />
                      <MiddlewareCompareRow
                        label="工具限制"
                        globalValue={middlewareDefaults.tool_limit_enabled}
                        agentValue={agent.middleware_flags?.tool_limit_enabled}
                      />
                    </TableBody>
                  </Table>
                  <div className="mt-3 flex justify-end">
                    <Button variant="ghost" size="sm" asChild>
                      <a href={`/admin/agents/${agent.id}`}>
                        编辑 Agent
                        <ChevronRight className="ml-1 h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* 原始配置查看 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">原始配置（只读）</CardTitle>
          <Button variant="outline" size="sm" onClick={loadRawConfig}>
            {showRawConfig ? "隐藏" : "查看"} JSON
          </Button>
        </CardHeader>
        {showRawConfig && rawConfig && (
          <CardContent>
            <pre className="max-h-96 overflow-auto rounded-lg bg-zinc-100 p-4 text-xs dark:bg-zinc-800">
              {JSON.stringify(rawConfig, null, 2)}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
