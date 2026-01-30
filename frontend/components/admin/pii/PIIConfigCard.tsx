"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Plus, ChevronDown } from "lucide-react";
import type { PIIRule } from "@/lib/api/agents";
import { PIIRuleItem } from "./PIIRuleItem";
import { PIIRuleForm } from "./PIIRuleForm";
import { PII_PRESETS } from "./constants";

interface PIIConfigCardProps {
  enabled: boolean;
  rules: PIIRule[];
  onEnabledChange: (enabled: boolean) => void;
  onRulesChange: (rules: PIIRule[]) => void;
}

export function PIIConfigCard({
  enabled,
  rules,
  onEnabledChange,
  onRulesChange,
}: PIIConfigCardProps) {
  const [isAddingRule, setIsAddingRule] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const handleAddRule = (rule: PIIRule) => {
    const newRule = { ...rule, id: crypto.randomUUID() };
    onRulesChange([...rules, newRule]);
    setIsAddingRule(false);
  };

  const handleUpdateRule = (updatedRule: PIIRule) => {
    onRulesChange(rules.map((r) => (r.id === updatedRule.id ? updatedRule : r)));
    setEditingRuleId(null);
  };

  const handleDeleteRule = (ruleId: string) => {
    onRulesChange(rules.filter((r) => r.id !== ruleId));
  };

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    onRulesChange(rules.map((r) => (r.id === ruleId ? { ...r, enabled } : r)));
  };

  const handleAddPreset = (presetType: string) => {
    const preset = PII_PRESETS.find((p) => p.type === presetType);
    if (!preset) return;

    // 检查是否已存在
    if (rules.some((r) => r.pii_type === presetType)) return;

    const newRule: PIIRule = {
      id: crypto.randomUUID(),
      pii_type: preset.type,
      strategy: "redact",
      detector: preset.detector,
      apply_to_input: true,
      apply_to_output: true,
      apply_to_tool_results: false,
      enabled: true,
    };
    onRulesChange([...rules, newRule]);
  };

  // 获取未添加的预设
  const availablePresets = PII_PRESETS.filter(
    (preset) => !rules.some((r) => r.pii_type === preset.type)
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">🛡️ PII 检测（隐私保护）</CardTitle>
            <CardDescription>
              检测并处理个人敏感信息，支持多规则配置
            </CardDescription>
          </div>
          <Switch checked={enabled} onCheckedChange={onEnabledChange} />
        </div>
      </CardHeader>

      {enabled && (
        <CardContent className="space-y-4">
          {/* 规则列表 */}
          {rules.length > 0 && (
            <div className="space-y-2">
              {rules.map((rule) =>
                editingRuleId === rule.id ? (
                  <PIIRuleForm
                    key={rule.id}
                    rule={rule}
                    onSave={handleUpdateRule}
                    onCancel={() => setEditingRuleId(null)}
                  />
                ) : (
                  <PIIRuleItem
                    key={rule.id}
                    rule={rule}
                    onEdit={() => setEditingRuleId(rule.id!)}
                    onDelete={() => handleDeleteRule(rule.id!)}
                    onToggle={(enabled: boolean) => handleToggleRule(rule.id!, enabled)}
                  />
                )
              )}
            </div>
          )}

          {/* 空状态 */}
          {rules.length === 0 && !isAddingRule && (
            <div className="text-center py-6 text-zinc-500">
              <p className="text-sm">暂无检测规则</p>
              <p className="text-xs mt-1">点击下方按钮添加规则</p>
            </div>
          )}

          {/* 添加规则表单 */}
          {isAddingRule && (
            <PIIRuleForm
              onSave={handleAddRule}
              onCancel={() => setIsAddingRule(false)}
            />
          )}

          {/* 操作按钮 */}
          {!isAddingRule && !editingRuleId && (
            <div className="flex flex-wrap gap-2 pt-2">
              {/* 添加预设（下拉菜单） */}
              {availablePresets.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Plus className="h-3 w-3 mr-1" />
                      添加预设
                      <ChevronDown className="h-3 w-3 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    {availablePresets.map((preset) => (
                      <DropdownMenuItem
                        key={preset.type}
                        onClick={() => handleAddPreset(preset.type)}
                      >
                        {preset.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
              {/* 自定义规则 */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsAddingRule(true)}
              >
                <Plus className="h-3 w-3 mr-1" />
                自定义规则
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
