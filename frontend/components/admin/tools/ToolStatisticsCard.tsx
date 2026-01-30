"use client";

import { BarChart3 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface ToolStatisticsCardProps {
  agentId?: string;
  title?: string;
}

export function ToolStatisticsCard({
  title = "工具调用统计",
}: ToolStatisticsCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-zinc-500" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex h-32 items-center justify-center rounded-lg bg-zinc-50 dark:bg-zinc-900">
          <p className="text-sm text-zinc-400">统计数据开发中...</p>
        </div>
      </CardContent>
    </Card>
  );
}
