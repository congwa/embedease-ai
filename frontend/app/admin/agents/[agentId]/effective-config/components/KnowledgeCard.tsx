"use client";

import { Database, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EffectiveConfigResponse } from "@/lib/api/agents";
import { getKnowledgeTypeLabel } from "@/lib/config/labels";

interface KnowledgeCardProps {
  knowledge: EffectiveConfigResponse["knowledge"];
}

export function KnowledgeCard({ knowledge }: KnowledgeCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-indigo-500" />
          <CardTitle className="text-base">知识源配置</CardTitle>
          <Badge variant={knowledge.configured ? "default" : "secondary"}>
            {knowledge.configured ? "已配置" : "未配置"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {knowledge.configured ? (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">名称:</span>
                <span className="ml-2 font-medium">{knowledge.name}</span>
              </div>
              <div>
                <span className="text-muted-foreground">类型:</span>
                <span className="ml-2 font-medium">{getKnowledgeTypeLabel(knowledge.type || "")}</span>
              </div>
              <div>
                <span className="text-muted-foreground">检索数量:</span>
                <span className="ml-2 font-medium">{knowledge.top_k}</span>
              </div>
              <div>
                <span className="text-muted-foreground">重排序:</span>
                <span className="ml-2 font-medium">{knowledge.rerank_enabled ? "启用" : "禁用"}</span>
              </div>
            </div>
            {knowledge.index_name && (
              <div className="text-sm">
                <span className="text-muted-foreground">索引:</span>
                <span className="ml-2 font-mono text-xs">{knowledge.index_name}</span>
              </div>
            )}
            {knowledge.data_version && (
              <div className="text-sm">
                <span className="text-muted-foreground">版本:</span>
                <span className="ml-2 font-mono text-xs">{knowledge.data_version}</span>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-2 text-muted-foreground">
            <AlertTriangle className="h-4 w-4" />
            <span>此 Agent 未配置知识源</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
