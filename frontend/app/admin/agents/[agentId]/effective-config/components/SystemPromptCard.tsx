"use client";

import { useState } from "react";
import { FileText, Copy, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { EffectiveConfigResponse, PromptLayer } from "@/lib/api/agents";
import { getPromptLayerLabel } from "@/lib/config/labels";

interface SystemPromptCardProps {
  systemPrompt: EffectiveConfigResponse["system_prompt"];
  onCopy: () => void;
}

export function SystemPromptCard({ systemPrompt, onCopy }: SystemPromptCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showLayers, setShowLayers] = useState(false);

  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-500" />
            <CardTitle className="text-base">系统提示词</CardTitle>
            <Badge variant="secondary">{systemPrompt.char_count} 字符</Badge>
          </div>
          <Button variant="ghost" size="sm" onClick={onCopy}>
            <Copy className="h-4 w-4" />
          </Button>
        </div>
        <CardDescription>最终生效的完整系统提示词</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 最终提示词内容 */}
        <Collapsible open={expanded} onOpenChange={setExpanded}>
          <CollapsibleTrigger asChild>
            <Button variant="outline" className="w-full justify-between">
              <span>查看完整内容</span>
              {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <ScrollArea className="h-[300px] rounded-md border bg-muted/50 p-4">
              <pre className="whitespace-pre-wrap text-sm">{systemPrompt.final_content}</pre>
            </ScrollArea>
          </CollapsibleContent>
        </Collapsible>

        {/* 来源追踪 */}
        <Collapsible open={showLayers} onOpenChange={setShowLayers}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between text-muted-foreground">
              <span>来源追踪 ({systemPrompt.layers.length} 层)</span>
              {showLayers ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <div className="space-y-2">
              {systemPrompt.layers.map((layer, i) => (
                <LayerItem key={i} layer={layer} index={i + 1} />
              ))}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}

function LayerItem({ layer, index }: { layer: PromptLayer; index: number }) {
  const getLayerColor = (name: string) => {
    switch (name) {
      case "base":
        return "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300";
      case "mode_suffix":
        return "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300";
      case "skill_injection":
        return "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <div className="flex items-center justify-between rounded-md border p-3">
      <div className="flex items-center gap-3">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-medium">
          {index}
        </span>
        <Badge className={getLayerColor(layer.name)}>{getPromptLayerLabel(layer.name).label}</Badge>
        <span className="text-sm text-muted-foreground">{layer.source}</span>
      </div>
      <span className="text-sm font-medium">{layer.char_count} 字符</span>
    </div>
  );
}
