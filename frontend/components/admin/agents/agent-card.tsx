"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bot, ChevronRight, Database, HelpCircle, Network, Wrench, Zap } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/admin/status-badge";
import { useAgentStore } from "@/stores";
import type { Agent } from "@/lib/api/agents";
import { cn } from "@/lib/utils";

const typeConfig: Record<string, { label: string; color: string }> = {
  product: { label: "商品推荐", color: "bg-blue-100 text-blue-700" },
  faq: { label: "FAQ 问答", color: "bg-green-100 text-green-700" },
  kb: { label: "知识库", color: "bg-purple-100 text-purple-700" },
  custom: { label: "自定义", color: "bg-zinc-100 text-zinc-700" },
};

interface AgentCardProps {
  agent: Agent;
  className?: string;
}

export function AgentCard({ agent, className }: AgentCardProps) {
  const router = useRouter();
  const activeAgent = useAgentStore((s) => s.activeAgent());
  const activateAgent = useAgentStore((s) => s.activateAgent);
  const [isActivating, setIsActivating] = useState(false);
  const typeInfo = typeConfig[agent.type] || typeConfig.custom;
  const isActive = activeAgent?.id === agent.id;

  const capabilities = [];
  if (agent.tool_categories?.includes("faq")) capabilities.push("faq");
  if (agent.tool_categories?.includes("search")) capabilities.push("search");
  if (agent.knowledge_config_id) capabilities.push("kb");

  const handleActivate = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsActivating(true);
    const success = await activateAgent(agent.id);
    setIsActivating(false);
    if (success) {
      router.push(`/admin/agents/${agent.id}`);
    }
  };

  return (
    <Link href={`/admin/agents/${agent.id}`}>
      <Card
        className={cn(
          "group cursor-pointer transition-all hover:border-zinc-300 hover:shadow-sm dark:hover:border-zinc-700",
          isActive && "border-green-300 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20",
          className
        )}
      >
        <CardContent className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-800">
                <Bot className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-zinc-900 dark:text-zinc-100">
                    {agent.name}
                  </h3>
                  {isActive && (
                    <Badge className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 text-xs">
                      <Zap className="mr-1 h-3 w-3" />
                      激活
                    </Badge>
                  )}
                  {agent.is_default && !isActive && (
                    <Badge variant="secondary" className="text-xs">
                      默认
                    </Badge>
                  )}
                  {agent.is_supervisor && (
                    <Badge className="bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300 text-xs">
                      <Network className="mr-1 h-3 w-3" />
                      Supervisor
                    </Badge>
                  )}
                </div>
                <p className="mt-1 line-clamp-1 text-sm text-zinc-500">
                  {agent.description || "暂无描述"}
                </p>
              </div>
            </div>
            <ChevronRight className="h-5 w-5 text-zinc-300 transition-colors group-hover:text-zinc-500" />
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge className={cn(typeInfo.color, `hover:${typeInfo.color}`)}>
                {typeInfo.label}
              </Badge>
              <StatusBadge
                enabled={agent.status === "enabled"}
                size="sm"
              />
            </div>

            <div className="flex items-center gap-1">
              {!isActive && agent.status === "enabled" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs"
                  onClick={handleActivate}
                  disabled={isActivating}
                >
                  {isActivating ? (
                    <span className="animate-pulse">激活中...</span>
                  ) : (
                    <>
                      <Zap className="mr-1 h-3 w-3" />
                      设为激活
                    </>
                  )}
                </Button>
              )}
              <div className="flex items-center gap-1 text-zinc-400 ml-2">
                {agent.knowledge_config_id && (
                  <Database className="h-4 w-4" />
                )}
                {agent.tool_categories?.includes("faq") && (
                  <HelpCircle className="h-4 w-4" />
                )}
                {agent.tool_categories && agent.tool_categories.length > 0 && (
                  <Wrench className="h-4 w-4" />
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
