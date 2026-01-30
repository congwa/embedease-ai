"use client";

import { useState } from "react";
import { Wrench, ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { getToolCategoryLabel } from "@/lib/config/labels";
import { cn } from "@/lib/utils";

export interface ToolCategoriesDisplayProps {
  categories: string[] | null;
  title?: string;
  description?: string;
  showToolDetails?: boolean;
  defaultExpanded?: boolean;
}

export function ToolCategoriesDisplay({
  categories,
  title = "可用功能",
  description = "Agent 可以使用的工具能力，点击展开查看具体工具",
  showToolDetails = true,
  defaultExpanded = false,
}: ToolCategoriesDisplayProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    defaultExpanded && categories ? new Set(categories) : new Set()
  );

  const toggleCategory = (cat: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Wrench className="h-4 w-4 text-zinc-500" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {categories && categories.length > 0 ? (
          <div className="space-y-2">
            {categories.map((category) => {
              const info = getToolCategoryLabel(category);
              const IconComponent = info.icon;
              const isExpanded = expandedCategories.has(category);
              return (
                <div
                  key={category}
                  className="rounded-lg border bg-zinc-50/50 dark:bg-zinc-800/30"
                >
                  <button
                    type="button"
                    onClick={() => showToolDetails && toggleCategory(category)}
                    className={cn(
                      "flex w-full items-center justify-between p-3 text-left rounded-lg transition-colors",
                      showToolDetails && "hover:bg-zinc-100 dark:hover:bg-zinc-800/50 cursor-pointer"
                    )}
                    disabled={!showToolDetails}
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-white dark:bg-zinc-700 text-zinc-600 dark:text-zinc-300">
                        <IconComponent className="h-4 w-4" />
                      </div>
                      <div>
                        <span className="font-medium">{info.label}</span>
                        <p className="text-xs text-zinc-500">{info.desc}</p>
                      </div>
                    </div>
                    {showToolDetails && info.tools && info.tools.length > 0 && (
                      <ChevronDown
                        className={cn(
                          "h-4 w-4 text-zinc-400 transition-transform",
                          isExpanded && "rotate-180"
                        )}
                      />
                    )}
                  </button>
                  {showToolDetails && isExpanded && info.tools && info.tools.length > 0 && (
                    <div className="border-t px-3 py-2 space-y-1">
                      {info.tools.map((tool) => (
                        <div
                          key={tool.name}
                          className="flex items-center gap-2 py-1 pl-11 text-sm"
                        >
                          <span className="text-zinc-400">•</span>
                          <code className="text-xs bg-zinc-100 dark:bg-zinc-700 px-1.5 py-0.5 rounded">
                            {tool.name}
                          </code>
                          <span className="text-zinc-500">{tool.desc}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">未限制工具类别，可使用所有工具</p>
        )}
      </CardContent>
    </Card>
  );
}
