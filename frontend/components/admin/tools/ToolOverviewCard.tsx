"use client";

import { ToolCategoriesDisplay } from "./ToolCategoriesDisplay";
import { ToolPolicyDisplay } from "./ToolPolicyDisplay";
import { ToolStatisticsCard } from "./ToolStatisticsCard";
import type { Agent } from "@/lib/api/agents";

export type ToolOverviewVariant = "default" | "single" | "multi";

export interface ToolOverviewCardProps {
  agent: Agent;
  variant?: ToolOverviewVariant;
  showStatistics?: boolean;
  showToolDetails?: boolean;
}

const VARIANT_LABELS: Record<ToolOverviewVariant, { categoryTitle: string; categoryDesc: string }> = {
  default: {
    categoryTitle: "可用功能",
    categoryDesc: "Agent 可以使用的工具能力，点击展开查看具体工具",
  },
  single: {
    categoryTitle: "可用功能",
    categoryDesc: "Agent 可以使用的工具能力，点击展开查看具体工具",
  },
  multi: {
    categoryTitle: "可用功能",
    categoryDesc: "子 Agent 可以使用的工具能力",
  },
};

export function ToolOverviewCard({
  agent,
  variant = "default",
  showStatistics = false,
  showToolDetails = true,
}: ToolOverviewCardProps) {
  const labels = VARIANT_LABELS[variant];

  return (
    <div className="space-y-6">
      <ToolCategoriesDisplay
        categories={agent.tool_categories}
        title={labels.categoryTitle}
        description={labels.categoryDesc}
        showToolDetails={showToolDetails}
      />

      <ToolPolicyDisplay
        policy={agent.tool_policy}
        showFullDetails={variant !== "multi"}
      />

      {showStatistics && <ToolStatisticsCard agentId={agent.id} />}
    </div>
  );
}
