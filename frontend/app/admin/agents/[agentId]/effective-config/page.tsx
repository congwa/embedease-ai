"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { RefreshCw, Copy, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getAgentEffectiveConfig, type EffectiveConfigResponse } from "@/lib/api/agents";
import { getModeLabel } from "@/lib/config/labels";
import {
  HealthCard,
  SystemPromptCard,
  SkillsCard,
  ToolsCard,
  MiddlewaresCard,
  KnowledgeCard,
  PoliciesCard,
} from "./components";

export default function EffectiveConfigPage() {
  const params = useParams();
  const agentId = params.agentId as string;

  const [config, setConfig] = useState<EffectiveConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAgentEffectiveConfig(agentId);
      setConfig(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, [agentId]);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    // 简单提示，可替换为项目的 toast 组件
    alert(`已复制${label}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">加载运行态配置...</span>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
        <AlertTriangle className="mx-auto h-8 w-8 text-destructive" />
        <p className="mt-2 text-destructive">{error || "加载失败"}</p>
        <Button variant="outline" className="mt-4" onClick={fetchConfig}>
          重试
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 顶部信息栏 */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">运行态配置预览</h2>
          <p className="text-sm text-muted-foreground">
            版本: {config.config_version} · 模式: {getModeLabel(config.mode)} · 生成于{" "}
            {new Date(config.generated_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchConfig}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              copyToClipboard(JSON.stringify(config, null, 2), "完整配置");
            }}
          >
            <Copy className="mr-2 h-4 w-4" />
            导出 JSON
          </Button>
        </div>
      </div>

      {/* 健康度卡片 */}
      <HealthCard health={config.health} />

      {/* 主要内容区域 */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* 系统提示词 */}
        <SystemPromptCard
          systemPrompt={config.system_prompt}
          onCopy={() => copyToClipboard(config.system_prompt.final_content, "系统提示词")}
        />

        {/* 技能清单 */}
        <SkillsCard skills={config.skills} />

        {/* 工具清单 */}
        <ToolsCard tools={config.tools} />

        {/* 中间件链 */}
        <MiddlewaresCard middlewares={config.middlewares} />

        {/* 知识源配置 */}
        <KnowledgeCard knowledge={config.knowledge} />

        {/* 策略配置 */}
        <PoliciesCard policies={config.policies} />
      </div>
    </div>
  );
}
