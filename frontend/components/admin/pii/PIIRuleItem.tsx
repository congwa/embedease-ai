"use client";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Pencil, Trash2 } from "lucide-react";
import type { PIIRule } from "@/lib/api/agents";
import { getPIITypeLabel, isBuiltinType, getStrategyInfo } from "./constants";

interface PIIRuleItemProps {
  rule: PIIRule;
  onEdit: () => void;
  onDelete: () => void;
  onToggle: (enabled: boolean) => void;
}

export function PIIRuleItem({ rule, onEdit, onDelete, onToggle }: PIIRuleItemProps) {
  const strategyInfo = getStrategyInfo(rule.strategy);
  const isBuiltin = isBuiltinType(rule.pii_type);

  // 构建应用范围标签
  const scopeLabels: string[] = [];
  if (rule.apply_to_input) scopeLabels.push("输入");
  if (rule.apply_to_output) scopeLabels.push("输出");
  if (rule.apply_to_tool_results) scopeLabels.push("工具");

  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border ${
        rule.enabled ? "bg-zinc-50 dark:bg-zinc-900" : "bg-zinc-100/50 dark:bg-zinc-800/50 opacity-60"
      }`}
    >
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <Switch
          checked={rule.enabled}
          onCheckedChange={onToggle}
          className="shrink-0"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm truncate">
              {getPIITypeLabel(rule.pii_type)}
            </span>
            {!isBuiltin && (
              <Badge variant="outline" className="text-xs">
                自定义
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-zinc-500 mt-0.5">
            <span>{strategyInfo.icon} {strategyInfo.label}</span>
            <span>·</span>
            <span>{scopeLabels.join(" / ")}</span>
            {rule.detector && (
              <>
                <span>·</span>
                <span className="font-mono truncate max-w-[120px]" title={rule.detector}>
                  /{rule.detector}/
                </span>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0 ml-2">
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onEdit}>
          <Pencil className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-red-500 hover:text-red-600"
          onClick={onDelete}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
