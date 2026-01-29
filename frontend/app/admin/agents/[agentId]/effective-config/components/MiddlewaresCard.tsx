"use client";

import { useState } from "react";
import { Settings2, ChevronDown, ChevronRight, ArrowRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import type { EffectiveConfigResponse, MiddlewareInfo } from "@/lib/api/agents";
import { getMiddlewarePipelineLabel } from "@/lib/config/labels";

interface MiddlewaresCardProps {
  middlewares: EffectiveConfigResponse["middlewares"];
}

export function MiddlewaresCard({ middlewares }: MiddlewaresCardProps) {
  const [showDisabled, setShowDisabled] = useState(false);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Settings2 className="h-5 w-5 text-cyan-500" />
          <CardTitle className="text-base">中间件链</CardTitle>
          <Badge variant="secondary">
            {middlewares.pipeline.length} / {middlewares.pipeline.length + middlewares.disabled.length}
          </Badge>
        </div>
        <CardDescription>按执行顺序排列的中间件</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 管道可视化 */}
        <div className="flex flex-wrap items-center gap-1 rounded-md bg-muted/50 p-3 text-xs">
          {middlewares.pipeline.map((m, i) => (
            <span key={m.name} className="flex items-center">
              <Badge variant="outline">
                {getMiddlewarePipelineLabel(m.name).label}
              </Badge>
              {i < middlewares.pipeline.length - 1 && (
                <ArrowRight className="mx-1 h-3 w-3 text-muted-foreground" />
              )}
            </span>
          ))}
        </div>

        {/* 详细列表 */}
        <ScrollArea className="h-[200px]">
          <div className="space-y-2">
            {middlewares.pipeline.map((m, i) => (
              <MiddlewareItem key={m.name} middleware={m} index={i + 1} />
            ))}
          </div>
        </ScrollArea>

        {/* 未启用的中间件 */}
        {middlewares.disabled.length > 0 && (
          <Collapsible open={showDisabled} onOpenChange={setShowDisabled}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between text-muted-foreground">
                <span>未启用 ({middlewares.disabled.length})</span>
                {showDisabled ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              {middlewares.disabled.map((m) => (
                <MiddlewareItem key={m.name} middleware={m} disabled />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

function MiddlewareItem({
  middleware,
  index,
  disabled,
}: {
  middleware: MiddlewareInfo;
  index?: number;
  disabled?: boolean;
}) {
  const hasParams = Object.keys(middleware.params).length > 0;
  const pipelineLabel = getMiddlewarePipelineLabel(middleware.name);

  return (
    <div className={`rounded-md border p-3 ${disabled ? "border-dashed opacity-60" : ""}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          {index && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted text-xs">
              {index}
            </span>
          )}
          <span className={`h-2 w-2 rounded-full ${disabled ? "bg-red-500" : "bg-green-500"}`} />
          <span className="font-medium">{pipelineLabel.label}</span>
          <Badge variant="outline" className="text-xs">
            顺序: {middleware.order}
          </Badge>
        </div>
        <Badge variant={disabled ? "destructive" : "default"} className="text-xs">
          {disabled ? "禁用" : "启用"}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {pipelineLabel.desc}
      </p>
      {disabled && middleware.reason && (
        <p className="mt-1 text-xs text-destructive">{middleware.reason}</p>
      )}
      {hasParams && !disabled && (
        <div className="mt-2 rounded bg-muted/50 p-2 font-mono text-xs">
          {Object.entries(middleware.params).map(([k, v]) => (
            <div key={k}>
              {k}: {JSON.stringify(v)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
