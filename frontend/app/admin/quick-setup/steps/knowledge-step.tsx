"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShoppingCart,
  MessageCircleQuestion,
  BookOpen,
  Wrench,
  Loader2,
  Settings,
  ExternalLink,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { type StepProps } from "../page";
import { getAgents, getFAQStats, type Agent, type FAQStatsResponse } from "@/lib/api/agents";
import { getAgentTypeDefaults } from "@/lib/api/quick-setup";

const TYPE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  product: ShoppingCart,
  faq: MessageCircleQuestion,
  kb: BookOpen,
  custom: Wrench,
};

const TYPE_LABELS: Record<string, string> = {
  product: "商品推荐助手",
  faq: "FAQ 问答助手",
  kb: "知识库助手",
  custom: "自定义助手",
};

export function KnowledgeStep({
  state,
  agentTypes,
  onComplete,
  onSkip,
  isLoading,
}: StepProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(
    state.agent_id
  );
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [faqStats, setFaqStats] = useState<FAQStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [typeConfig, setTypeConfig] = useState<{
    tool_categories: string[];
    middleware_flags: Record<string, boolean>;
  } | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const agentsData = await getAgents({ limit: 100 });
        setAgents(agentsData.items);

        // 自动选择默认 Agent
        const defaultAgent = agentsData.items.find((a) => a.is_default);
        if (defaultAgent && !selectedAgentId) {
          setSelectedAgentId(defaultAgent.id);
          setSelectedAgent(defaultAgent);
        }
      } catch (e) {
        console.error("加载 Agent 列表失败", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [selectedAgentId]);

  useEffect(() => {
    const loadAgentDetails = async () => {
      if (!selectedAgentId) return;

      const agent = agents.find((a) => a.id === selectedAgentId);
      if (agent) {
        setSelectedAgent(agent);

        // 加载类型默认配置
        try {
          const defaults = await getAgentTypeDefaults(agent.type);
          setTypeConfig({
            tool_categories: defaults.tool_categories,
            middleware_flags: defaults.middleware_flags,
          });
        } catch (e) {
          console.error("加载类型配置失败", e);
        }

        // 如果是 FAQ 类型，加载统计
        if (agent.type === "faq") {
          try {
            const stats = await getFAQStats(agent.id);
            setFaqStats(stats);
          } catch (e) {
            console.error("加载 FAQ 统计失败", e);
          }
        } else {
          setFaqStats(null);
        }
      }
    };
    loadAgentDetails();
  }, [selectedAgentId, agents]);

  const handleComplete = () => {
    onComplete({
      agent_id: selectedAgentId,
      agent_type: selectedAgent?.type,
    });
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  const typeInfo = agentTypes.find((t) => t.type === selectedAgent?.type);
  const TypeIcon = selectedAgent ? TYPE_ICONS[selectedAgent.type] : Settings;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">知识 & Agent 配置</h2>
        <p className="text-zinc-500">
          选择要配置的 Agent，根据其类型进行差异化配置。
        </p>
      </div>

      {/* Agent 选择 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">选择 Agent</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select
            value={selectedAgentId || ""}
            onValueChange={(value) => setSelectedAgentId(value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="选择要配置的 Agent" />
            </SelectTrigger>
            <SelectContent>
              {agents.map((agent) => {
                const Icon = TYPE_ICONS[agent.type];
                return (
                  <SelectItem key={agent.id} value={agent.id}>
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span>{agent.name}</span>
                      {agent.is_default && (
                        <Badge variant="secondary" className="ml-2 text-xs">
                          默认
                        </Badge>
                      )}
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>

          {agents.length === 0 && (
            <div className="text-center py-4 text-zinc-500">
              <p>暂无 Agent，请先创建</p>
              <Button variant="outline" size="sm" className="mt-2" asChild>
                <Link href="/admin/agents">
                  前往创建 Agent
                  <ExternalLink className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 类型特定配置 */}
      {selectedAgent && (
        <>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <TypeIcon className="h-4 w-4" />
                {TYPE_LABELS[selectedAgent.type]}
                <Badge variant="outline">{selectedAgent.type}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-zinc-500">
                {typeInfo?.description || "暂无描述"}
              </p>

              {/* FAQ 特定信息 */}
              {selectedAgent.type === "faq" && faqStats && (
                <div className="rounded-lg border p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">FAQ 统计</span>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/admin/agents/${selectedAgent.id}/faq`}>
                        管理 FAQ
                        <ExternalLink className="ml-2 h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold">{faqStats.total}</div>
                      <div className="text-xs text-zinc-500">总数</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {faqStats.enabled}
                      </div>
                      <div className="text-xs text-zinc-500">已启用</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-amber-600">
                        {faqStats.unindexed}
                      </div>
                      <div className="text-xs text-zinc-500">未索引</div>
                    </div>
                  </div>
                  {faqStats.total === 0 && (
                    <div className="flex items-center gap-2 text-amber-600 text-sm">
                      <AlertTriangle className="h-4 w-4" />
                      请至少创建 1 条 FAQ 条目
                    </div>
                  )}
                </div>
              )}

              {/* 工具类别 */}
              {typeConfig && (
                <div className="space-y-2">
                  <Label>工具类别</Label>
                  <div className="flex flex-wrap gap-2">
                    {typeConfig.tool_categories.map((cat) => (
                      <Badge key={cat} variant="secondary">
                        {cat}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* 中间件开关 */}
              {typeConfig && (
                <div className="space-y-3">
                  <Label>中间件配置</Label>
                  <div className="grid gap-3 md:grid-cols-2">
                    {Object.entries(typeConfig.middleware_flags).map(
                      ([key, value]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between rounded-lg border p-3"
                        >
                          <span className="text-sm">
                            {key.replace(/_/g, " ").replace("enabled", "")}
                          </span>
                          <Switch checked={value} disabled />
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}

              {/* 提示信息 */}
              {typeInfo?.steps && (
                <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
                  <div className="text-sm font-medium mb-2">配置提示</div>
                  <ul className="text-sm text-zinc-600 dark:text-zinc-400 space-y-1">
                    {typeInfo.steps
                      .find((s) => s.step_key === "knowledge")
                      ?.hints.map((hint, i) => (
                        <li key={i}>• {hint}</li>
                      ))}
                  </ul>
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
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/admin/agents/${selectedAgent.id}`}>
                    编辑 Agent
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                {selectedAgent.type === "faq" && (
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/admin/agents/${selectedAgent.id}/faq`}>
                      管理 FAQ
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </Link>
                  </Button>
                )}
                <Button variant="outline" size="sm" asChild>
                  <Link href="/admin/knowledge">
                    知识源管理
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => onSkip()} disabled={isLoading}>
          跳过此步
        </Button>
        <Button
          onClick={handleComplete}
          disabled={isLoading || !selectedAgentId}
        >
          确认并继续
        </Button>
      </div>
    </div>
  );
}
