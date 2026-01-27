"use client";

import { useState } from "react";
import { ShoppingCart, HelpCircle, BookOpen, Settings, Check, ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StepProps } from "../page";

interface AgentType {
  id: "product" | "faq" | "kb" | "custom";
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  features: string[];
}

const AGENT_TYPES: AgentType[] = [
  {
    id: "product",
    title: "商品推荐",
    description: "商品搜索、对比、推荐",
    icon: ShoppingCart,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50 dark:bg-emerald-900/20",
    features: ["商品检索", "智能推荐", "对比分析"],
  },
  {
    id: "faq",
    title: "FAQ 问答",
    description: "常见问题自动回复",
    icon: HelpCircle,
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    features: ["精准匹配", "自动回复", "FAQ 管理"],
  },
  {
    id: "kb",
    title: "知识库",
    description: "文档知识库智能检索",
    icon: BookOpen,
    color: "text-purple-600",
    bgColor: "bg-purple-50 dark:bg-purple-900/20",
    features: ["文档解析", "语义检索", "知识问答"],
  },
  {
    id: "custom",
    title: "自定义",
    description: "完全自定义配置",
    icon: Settings,
    color: "text-zinc-600",
    bgColor: "bg-zinc-100 dark:bg-zinc-800",
    features: ["灵活配置", "自定义工具", "高级选项"],
  },
];

export function AgentTypeStep({ step, onComplete, isLoading }: StepProps) {
  const [selectedType, setSelectedType] = useState<string | null>(
    (step.data?.agent_type as string) || null
  );

  const handleSelect = async () => {
    if (!selectedType) return;
    await onComplete({ agent_type: selectedType });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold">选择 Agent 类型</h2>
        <p className="text-zinc-500">
          根据业务需求选择合适的 Agent 类型，后续步骤将根据类型提供相应配置
        </p>
      </div>

      {/* Type Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 max-w-4xl mx-auto">
        {AGENT_TYPES.map((type) => {
          const Icon = type.icon;
          const isSelected = selectedType === type.id;

          return (
            <Card
              key={type.id}
              className={cn(
                "cursor-pointer transition-all duration-200 hover:shadow-md relative",
                isSelected
                  ? "ring-2 ring-offset-2 ring-blue-500 shadow-md"
                  : "hover:border-zinc-300 dark:hover:border-zinc-600"
              )}
              onClick={() => setSelectedType(type.id)}
            >
              {/* Selected indicator */}
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <div className="w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                </div>
              )}

              <CardContent className="p-4 space-y-3">
                {/* Icon */}
                <div
                  className={cn(
                    "w-10 h-10 rounded-lg flex items-center justify-center",
                    type.bgColor
                  )}
                >
                  <Icon className={cn("h-5 w-5", type.color)} />
                </div>

                {/* Title & Description */}
                <div>
                  <h3 className="font-semibold">{type.title}</h3>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {type.description}
                  </p>
                </div>

                {/* Features */}
                <div className="flex flex-wrap gap-1">
                  {type.features.map((feature) => (
                    <span
                      key={feature}
                      className="text-xs px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400"
                    >
                      {feature}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Action Button */}
      <div className="flex justify-center pt-4">
        <Button
          size="lg"
          onClick={handleSelect}
          disabled={!selectedType || isLoading}
          className="min-w-[200px]"
        >
          选择此类型并继续
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
