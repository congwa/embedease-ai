"use client";

import { Settings2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export interface ToolPolicyConfig {
  allow_direct_answer: boolean;
  min_tool_calls: number;
  fallback_tool: string | null;
  clarification_tool: string | null;
}

export interface ToolPolicyConfigCardProps {
  config: ToolPolicyConfig;
  onConfigChange: (config: Partial<ToolPolicyConfig>) => void;
  availableTools?: string[];
  title?: string;
  description?: string;
}

export const DEFAULT_TOOL_POLICY: ToolPolicyConfig = {
  allow_direct_answer: true,
  min_tool_calls: 0,
  fallback_tool: null,
  clarification_tool: null,
};

export function ToolPolicyConfigCard({
  config,
  onConfigChange,
  availableTools = [],
  title = "工具调用策略",
  description = "控制 Agent 如何使用工具回答问题",
}: ToolPolicyConfigCardProps) {
  const cfg = { ...DEFAULT_TOOL_POLICY, ...config };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-zinc-500" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>允许直接回答</Label>
            <p className="text-xs text-zinc-500">
              {cfg.allow_direct_answer
                ? "可不调用工具直接回复简单问题"
                : "必须调用工具后才能回答"}
            </p>
          </div>
          <Switch
            checked={cfg.allow_direct_answer}
            onCheckedChange={(v) => onConfigChange({ allow_direct_answer: v })}
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>最少工具调用次数</Label>
            <span className="text-sm font-mono text-zinc-500">
              {cfg.min_tool_calls === 0 ? "不限" : cfg.min_tool_calls}
            </span>
          </div>
          <Slider
            min={0}
            max={5}
            step={1}
            value={[cfg.min_tool_calls]}
            onValueChange={([v]) => onConfigChange({ min_tool_calls: v })}
          />
          <p className="text-xs text-zinc-500">
            0 = 不限制，Agent 可以自行决定是否调用工具
          </p>
        </div>

        <div className="space-y-2">
          <Label>备选工具</Label>
          <Select
            value={cfg.fallback_tool || "__none__"}
            onValueChange={(v) =>
              onConfigChange({ fallback_tool: v === "__none__" ? null : v })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="选择备选工具" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">不设置</SelectItem>
              {availableTools.map((tool) => (
                <SelectItem key={tool} value={tool}>
                  {tool}
                </SelectItem>
              ))}
              {availableTools.length === 0 && (
                <>
                  <SelectItem value="faq_search">faq_search</SelectItem>
                  <SelectItem value="kb_search">kb_search</SelectItem>
                  <SelectItem value="guide_user">guide_user</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
          <p className="text-xs text-zinc-500">
            当其他工具无法回答时，使用此工具兜底
          </p>
        </div>

        <div className="space-y-2">
          <Label>澄清工具</Label>
          <Select
            value={cfg.clarification_tool || "__none__"}
            onValueChange={(v) =>
              onConfigChange({ clarification_tool: v === "__none__" ? null : v })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="选择澄清工具" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">不设置</SelectItem>
              {availableTools.map((tool) => (
                <SelectItem key={tool} value={tool}>
                  {tool}
                </SelectItem>
              ))}
              {availableTools.length === 0 && (
                <SelectItem value="guide_user">guide_user</SelectItem>
              )}
            </SelectContent>
          </Select>
          <p className="text-xs text-zinc-500">
            信息不足时用于引导用户明确需求
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
