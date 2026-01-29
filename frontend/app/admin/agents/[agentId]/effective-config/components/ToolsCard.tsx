"use client";

import { useState } from "react";
import { Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import type { EffectiveConfigResponse, ToolInfo, FilteredToolInfo } from "@/lib/api/agents";
import { getToolNameLabel } from "@/lib/config/labels";

interface ToolsCardProps {
  tools: EffectiveConfigResponse["tools"];
}

export function ToolsCard({ tools }: ToolsCardProps) {
  const [showFiltered, setShowFiltered] = useState(false);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Wrench className="h-5 w-5 text-orange-500" />
          <CardTitle className="text-base">工具清单</CardTitle>
          <Badge variant="secondary">{tools.enabled.length} 个启用</Badge>
        </div>
        <CardDescription>Agent 可调用的工具列表</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 启用的工具 */}
        <ScrollArea className="h-[200px]">
          <div className="space-y-2">
            {tools.enabled.map((tool) => (
              <ToolItem key={tool.name} tool={tool} />
            ))}
          </div>
        </ScrollArea>

        {/* 被过滤的工具 */}
        {tools.filtered.length > 0 && (
          <Collapsible open={showFiltered} onOpenChange={setShowFiltered}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="w-full justify-between text-muted-foreground">
                <span>被过滤的工具 ({tools.filtered.length})</span>
                {showFiltered ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 space-y-2">
              {tools.filtered.map((tool) => (
                <FilteredToolItem key={tool.name} tool={tool} />
              ))}
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}

function ToolItem({ tool }: { tool: ToolInfo }) {
  const toolLabel = getToolNameLabel(tool.name);
  return (
    <div className="flex items-start justify-between rounded-md border p-3">
      <div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          <span className="font-medium">{toolLabel.label}</span>
          <span className="font-mono text-xs text-muted-foreground">({tool.name})</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {toolLabel.desc || tool.description}
        </p>
        <div className="mt-1 flex flex-wrap gap-1">
          {tool.categories.map((c, i) => (
            <Badge key={i} variant="secondary" className="text-xs">
              {c}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}

function FilteredToolItem({ tool }: { tool: FilteredToolInfo }) {
  const toolLabel = getToolNameLabel(tool.name);
  return (
    <div className="flex items-start justify-between rounded-md border border-dashed p-3 opacity-60">
      <div>
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-red-500" />
          <span className="font-medium">{toolLabel.label}</span>
          <span className="font-mono text-xs text-muted-foreground">({tool.name})</span>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">{tool.reason}</p>
      </div>
    </div>
  );
}
