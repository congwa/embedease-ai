"use client";

import { Wrench, Check, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { TOOL_CATEGORY_LABELS, getToolCategoryLabel } from "@/lib/config/labels";

export interface ToolCategoriesConfig {
  categories: string[];
}

export interface ToolCategoriesConfigCardProps {
  config: ToolCategoriesConfig;
  onConfigChange: (config: ToolCategoriesConfig) => void;
  agentType?: string;
  title?: string;
  description?: string;
}

export const ALL_TOOL_CATEGORY_KEYS = Object.keys(TOOL_CATEGORY_LABELS);

export const DEFAULT_CATEGORIES_BY_TYPE: Record<string, string[]> = {
  product: ["search", "query", "compare", "filter", "category", "featured", "purchase", "guide"],
  faq: ["faq"],
  kb: ["kb", "search"],
  custom: [],
};

export function ToolCategoriesConfigCard({
  config,
  onConfigChange,
  agentType,
  title = "可用工具类别",
  description = "选择 Agent 可使用的工具功能范围",
}: ToolCategoriesConfigCardProps) {
  const toggleCategory = (cat: string) => {
    const newCategories = config.categories.includes(cat)
      ? config.categories.filter((c) => c !== cat)
      : [...config.categories, cat];
    onConfigChange({ categories: newCategories });
  };

  const selectAll = () => onConfigChange({ categories: [...ALL_TOOL_CATEGORY_KEYS] });
  const clearAll = () => onConfigChange({ categories: [] });
  const useDefaults = () => {
    if (agentType && DEFAULT_CATEGORIES_BY_TYPE[agentType]) {
      onConfigChange({ categories: [...DEFAULT_CATEGORIES_BY_TYPE[agentType]] });
    }
  };

  const selectedCount = config.categories.length;
  const totalCount = ALL_TOOL_CATEGORY_KEYS.length;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-zinc-500" />
            <CardTitle className="text-base">{title}</CardTitle>
          </div>
          <span className="text-sm text-zinc-500">
            已选 {selectedCount}/{totalCount}
          </span>
        </div>
        <CardDescription>{description}</CardDescription>
        <div className="flex gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={selectAll}>
            <Check className="mr-1 h-3 w-3" />
            全选
          </Button>
          <Button variant="outline" size="sm" onClick={clearAll}>
            清空
          </Button>
          {agentType && DEFAULT_CATEGORIES_BY_TYPE[agentType] && (
            <Button variant="outline" size="sm" onClick={useDefaults}>
              <RotateCcw className="mr-1 h-3 w-3" />
              恢复默认
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-2">
          {ALL_TOOL_CATEGORY_KEYS.map((cat) => {
            const info = getToolCategoryLabel(cat);
            const IconComponent = info.icon;
            const isChecked = config.categories.includes(cat);
            return (
              <label
                key={cat}
                className="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
              >
                <Checkbox
                  checked={isChecked}
                  onCheckedChange={() => toggleCategory(cat)}
                  className="mt-0.5"
                />
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                  <IconComponent className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium">{info.label}</p>
                  <p className="text-xs text-zinc-500 truncate">{info.desc}</p>
                  {info.tools && info.tools.length > 0 && (
                    <p className="mt-1 text-xs text-zinc-400">
                      {info.tools.length} 个工具
                    </p>
                  )}
                </div>
              </label>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
