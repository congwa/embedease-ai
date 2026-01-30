/**
 * 工具策略字段标签配置
 */

import { CheckCircle, Gauge, LifeBuoy, HelpCircle, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface ToolPolicyFieldInfo {
  label: string;
  desc: string;
  icon: LucideIcon;
}

export const TOOL_POLICY_FIELD_LABELS: Record<string, ToolPolicyFieldInfo> = {
  allow_direct_answer: {
    label: "允许直接回答",
    desc: "Agent 是否可以不调用工具直接回复",
    icon: CheckCircle,
  },
  min_tool_calls: {
    label: "最少工具调用",
    desc: "每次对话至少调用工具的次数",
    icon: Gauge,
  },
  fallback_tool: {
    label: "备选工具",
    desc: "其他工具无法回答时的兜底工具",
    icon: LifeBuoy,
  },
  clarification_tool: {
    label: "澄清工具",
    desc: "信息不足时用于引导用户的工具",
    icon: HelpCircle,
  },
};

export function getToolPolicyFieldLabel(field: string): ToolPolicyFieldInfo {
  return (
    TOOL_POLICY_FIELD_LABELS[field] || {
      label: field,
      desc: "",
      icon: Settings,
    }
  );
}
