"use client";

import { Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { EffectiveConfigResponse } from "@/lib/api/agents";
import { getModeLabel, getPolicyFieldLabel, getConfigSourceLabel } from "@/lib/config/labels";

interface PoliciesCardProps {
  policies: EffectiveConfigResponse["policies"];
}

export function PoliciesCard({ policies }: PoliciesCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-emerald-500" />
          <CardTitle className="text-base">策略配置</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 回答模式 */}
        <div>
          <span className="text-sm text-muted-foreground">回答模式:</span>
          <Badge className="ml-2">{getModeLabel(policies.mode)}</Badge>
        </div>

        <Separator />

        {/* 工具策略 */}
        {policies.tool_policy && (
          <div className="space-y-2">
            <p className="text-sm font-medium">工具调用策略</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <PolicyItem
                label="最小调用次数"
                value={policies.tool_policy.min_tool_calls}
              />
              <PolicyItem
                label="允许直接回答"
                value={policies.tool_policy.allow_direct_answer}
              />
            </div>
          </div>
        )}

        <Separator />

        {/* 中间件 Flags */}
        <div className="space-y-2">
          <p className="text-sm font-medium">中间件开关</p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(policies.middleware_flags).map(([key, pv]) => (
              <PolicyItem key={key} fieldKey={key} value={pv} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PolicyItem({
  fieldKey,
  value,
  label,
}: {
  fieldKey?: string;
  value: { value: unknown; source: string };
  label?: string;
}) {
  const fieldLabel = fieldKey ? getPolicyFieldLabel(fieldKey) : null;
  const displayLabel = label || fieldLabel?.label || fieldKey || "";
  const displayValue = typeof value.value === "boolean" ? (value.value ? "是" : "否") : String(value.value);
  const sourceLabel = getConfigSourceLabel(value.source);
  const sourceColor =
    value.source === "agent"
      ? "text-green-600"
      : value.source === "settings"
        ? "text-blue-600"
        : "text-gray-600";

  return (
    <div className="flex items-center justify-between rounded border p-2">
      <span className="text-muted-foreground">{displayLabel}</span>
      <div className="text-right">
        <span className="font-medium">{displayValue}</span>
        <span className={`ml-1 text-xs ${sourceColor}`}>({sourceLabel})</span>
      </div>
    </div>
  );
}
