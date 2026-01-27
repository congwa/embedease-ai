"use client";

import { useState } from "react";
import { Bot, Network, Check, ArrowRight, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { setSetupMode } from "@/lib/api/quick-setup";
import type { StepProps } from "../page";

interface ModeOption {
  id: "single" | "supervisor";
  title: string;
  description: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  features: string[];
  recommended: string[];
}

const MODE_OPTIONS: ModeOption[] = [
  {
    id: "single",
    title: "单 Agent 模式",
    description: "适合简单场景，一个 Agent 处理所有用户请求",
    icon: Bot,
    color: "text-blue-600",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    features: ["配置简单", "响应快速", "资源占用少"],
    recommended: ["FAQ 问答", "商品推荐", "知识库检索"],
  },
  {
    id: "supervisor",
    title: "Supervisor 模式",
    description: "适合复杂多领域场景，多个 Agent 协作，智能路由分发",
    icon: Network,
    color: "text-orange-600",
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    features: ["支持多领域", "自动路由", "专业分工"],
    recommended: ["综合客服", "多业务线", "智能调度"],
  },
];

export function ModeStep({ step, onComplete, isLoading }: StepProps) {
  const [selectedMode, setSelectedMode] = useState<"single" | "supervisor" | null>(
    (step.data?.mode as "single" | "supervisor") || null
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSelect = async () => {
    if (!selectedMode) return;
    
    try {
      setIsSubmitting(true);
      await setSetupMode(selectedMode);
      await onComplete({ mode: selectedMode });
    } catch (error) {
      console.error("设置模式失败:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white mb-4">
          <Sparkles className="h-8 w-8" />
        </div>
        <h2 className="text-2xl font-bold">选择运行模式</h2>
        <p className="text-zinc-500 max-w-md mx-auto">
          根据您的业务场景选择合适的模式，后续可在设置中随时切换
        </p>
      </div>

      {/* Mode Cards */}
      <div className="grid gap-4 md:grid-cols-2 max-w-3xl mx-auto">
        {MODE_OPTIONS.map((option) => {
          const Icon = option.icon;
          const isSelected = selectedMode === option.id;

          return (
            <Card
              key={option.id}
              className={cn(
                "cursor-pointer transition-all duration-200 hover:shadow-lg relative overflow-hidden",
                isSelected
                  ? "ring-2 ring-offset-2 ring-blue-500 shadow-lg"
                  : "hover:border-zinc-300 dark:hover:border-zinc-600"
              )}
              onClick={() => setSelectedMode(option.id)}
            >
              {/* Selected indicator */}
              {isSelected && (
                <div className="absolute top-3 right-3">
                  <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                </div>
              )}

              <CardContent className="p-6 space-y-4">
                {/* Icon & Title */}
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      "w-12 h-12 rounded-xl flex items-center justify-center",
                      option.bgColor
                    )}
                  >
                    <Icon className={cn("h-6 w-6", option.color)} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{option.title}</h3>
                    <p className="text-sm text-zinc-500 mt-1">
                      {option.description}
                    </p>
                  </div>
                </div>

                {/* Features */}
                <div className="space-y-2">
                  <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
                    特性
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {option.features.map((feature) => (
                      <span
                        key={feature}
                        className="inline-flex items-center px-2 py-1 rounded-md bg-zinc-100 dark:bg-zinc-800 text-xs"
                      >
                        <Check className="h-3 w-3 mr-1 text-green-500" />
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Recommended */}
                <div className="space-y-2">
                  <div className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
                    推荐场景
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {option.recommended.map((rec) => (
                      <span
                        key={rec}
                        className={cn(
                          "text-xs px-2 py-0.5 rounded-full",
                          option.bgColor,
                          option.color
                        )}
                      >
                        {rec}
                      </span>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Tip */}
      <div className="text-center text-sm text-zinc-500">
        <span className="inline-flex items-center gap-1">
          💡 选择后可在
          <span className="font-medium text-zinc-700 dark:text-zinc-300">
            设置 → Supervisor 配置
          </span>
          中随时切换模式
        </span>
      </div>

      {/* Action Button */}
      <div className="flex justify-center">
        <Button
          size="lg"
          onClick={handleSelect}
          disabled={!selectedMode || isLoading || isSubmitting}
          className="min-w-[200px]"
        >
          {isSubmitting ? (
            "正在设置..."
          ) : (
            <>
              选择此模式并继续
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
