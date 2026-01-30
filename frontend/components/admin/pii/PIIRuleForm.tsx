"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Check, X } from "lucide-react";
import type { PIIRule } from "@/lib/api/agents";
import { PII_PRESETS, STRATEGY_OPTIONS, isBuiltinType, getStrategyInfo, type PIIStrategy } from "./constants";

interface PIIRuleFormProps {
  rule?: PIIRule;
  onSave: (rule: PIIRule) => void;
  onCancel: () => void;
}

export function PIIRuleForm({ rule, onSave, onCancel }: PIIRuleFormProps) {
  const isEditing = !!rule;

  const [formData, setFormData] = useState<PIIRule>({
    id: rule?.id,
    pii_type: rule?.pii_type || "",
    strategy: rule?.strategy || "redact",
    detector: rule?.detector || null,
    apply_to_input: rule?.apply_to_input ?? true,
    apply_to_output: rule?.apply_to_output ?? true,
    apply_to_tool_results: rule?.apply_to_tool_results ?? false,
    enabled: rule?.enabled ?? true,
  });

  const [useCustomType, setUseCustomType] = useState(
    isEditing ? !isBuiltinType(rule.pii_type) && !PII_PRESETS.some((p) => p.type === rule.pii_type) : false
  );

  const handlePresetChange = (type: string) => {
    const preset = PII_PRESETS.find((p) => p.type === type);
    setFormData((prev) => ({
      ...prev,
      pii_type: type,
      detector: preset?.detector || null,
    }));
  };

  const handleSubmit = () => {
    if (!formData.pii_type.trim()) return;
    onSave(formData);
  };

  return (
    <div className="p-4 rounded-lg border bg-zinc-50 dark:bg-zinc-900 space-y-4">
      {/* 类型选择 */}
      <div className="space-y-2">
        <Label>PII 类型</Label>
        <div className="flex gap-2">
          {!useCustomType ? (
            <Select value={formData.pii_type} onValueChange={handlePresetChange}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="选择预设类型" />
              </SelectTrigger>
              <SelectContent>
                {PII_PRESETS.map((preset) => (
                  <SelectItem key={preset.type} value={preset.type}>
                    {preset.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              placeholder="自定义类型名称"
              value={formData.pii_type}
              onChange={(e) => setFormData((prev) => ({ ...prev, pii_type: e.target.value }))}
              className="flex-1"
            />
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setUseCustomType(!useCustomType);
              if (!useCustomType) {
                setFormData((prev) => ({ ...prev, pii_type: "", detector: "" }));
              }
            }}
          >
            {useCustomType ? "预设" : "自定义"}
          </Button>
        </div>
      </div>

      {/* 自定义正则 */}
      {(useCustomType || formData.detector) && (
        <div className="space-y-2">
          <Label>正则表达式</Label>
          <Input
            placeholder="如: 1[3-9]\d{9}"
            value={formData.detector || ""}
            onChange={(e) => setFormData((prev) => ({ ...prev, detector: e.target.value || null }))}
            className="font-mono text-sm"
          />
          <p className="text-xs text-zinc-500">内置类型无需填写正则，自定义类型必填</p>
        </div>
      )}

      {/* 处理策略 */}
      <div className="space-y-2">
        <Label>处理策略</Label>
        <Select
          value={formData.strategy}
          onValueChange={(v) => setFormData((prev) => ({ ...prev, strategy: v as PIIStrategy }))}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STRATEGY_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                <span>{opt.icon} {opt.label}</span>
                <span className="text-xs text-zinc-500 ml-2">{opt.desc}</span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 应用范围 */}
      <div className="space-y-2">
        <Label>应用范围</Label>
        <div className="flex flex-wrap gap-2">
          <Badge
            variant={formData.apply_to_input ? "default" : "outline"}
            className="cursor-pointer select-none"
            onClick={() => setFormData((prev) => ({ ...prev, apply_to_input: !prev.apply_to_input }))}
          >
            📥 用户输入
          </Badge>
          <Badge
            variant={formData.apply_to_output ? "default" : "outline"}
            className="cursor-pointer select-none"
            onClick={() => setFormData((prev) => ({ ...prev, apply_to_output: !prev.apply_to_output }))}
          >
            📤 Agent 输出
          </Badge>
          <Badge
            variant={formData.apply_to_tool_results ? "default" : "outline"}
            className="cursor-pointer select-none"
            onClick={() => setFormData((prev) => ({ ...prev, apply_to_tool_results: !prev.apply_to_tool_results }))}
          >
            🔧 工具结果
          </Badge>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          <X className="h-4 w-4 mr-1" />
          取消
        </Button>
        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={!formData.pii_type.trim()}
        >
          <Check className="h-4 w-4 mr-1" />
          {isEditing ? "保存" : "添加"}
        </Button>
      </div>
    </div>
  );
}
