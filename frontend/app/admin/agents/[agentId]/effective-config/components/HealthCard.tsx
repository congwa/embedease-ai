"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { EffectiveConfigResponse } from "@/lib/api/agents";

interface HealthCardProps {
  health: EffectiveConfigResponse["health"];
}

export function HealthCard({ health }: HealthCardProps) {
  const [showAllPassed, setShowAllPassed] = useState(false);
  const [showAllWarnings, setShowAllWarnings] = useState(false);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return "bg-green-500";
    if (score >= 60) return "bg-yellow-500";
    return "bg-red-500";
  };

  const COLLAPSE_THRESHOLD = 4;
  const passedToShow = showAllPassed ? health.passed : health.passed.slice(0, COLLAPSE_THRESHOLD);
  const warningsToShow = showAllWarnings ? health.warnings : health.warnings.slice(0, COLLAPSE_THRESHOLD);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">配置健康度</CardTitle>
          <div className="flex items-center gap-2">
            <div className={`text-3xl font-bold ${getScoreColor(health.score)}`}>
              {health.score}
              <span className="text-lg font-normal text-muted-foreground">%</span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Progress value={health.score} className={`h-2 ${getProgressColor(health.score)}`} />

        <div className="grid gap-4 sm:grid-cols-2">
          {/* 警告项 */}
          {health.warnings.length > 0 && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50/50 p-3 dark:border-yellow-900 dark:bg-yellow-950/20">
              <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-yellow-700 dark:text-yellow-400">
                <AlertTriangle className="h-4 w-4" />
                警告 ({health.warnings.length})
              </p>
              <div className="space-y-1">
                {warningsToShow.map((w, i) => (
                  <p key={i} className="text-sm text-yellow-600 dark:text-yellow-300">
                    • {w}
                  </p>
                ))}
              </div>
              {health.warnings.length > COLLAPSE_THRESHOLD && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2 h-7 w-full text-xs text-yellow-600 hover:text-yellow-700"
                  onClick={() => setShowAllWarnings(!showAllWarnings)}
                >
                  {showAllWarnings ? "收起" : `展开全部 ${health.warnings.length} 项`}
                  {showAllWarnings ? <ChevronDown className="ml-1 h-3 w-3" /> : <ChevronRight className="ml-1 h-3 w-3" />}
                </Button>
              )}
            </div>
          )}

          {/* 通过项 */}
          <div className={`rounded-lg border border-green-200 bg-green-50/50 p-3 dark:border-green-900 dark:bg-green-950/20 ${health.warnings.length === 0 ? "sm:col-span-2" : ""}`}>
            <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-green-700 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              通过 ({health.passed.length})
            </p>
            <div className={`space-y-1 ${health.warnings.length === 0 ? "sm:columns-2 sm:gap-4" : ""}`}>
              {passedToShow.map((p, i) => (
                <p key={i} className="text-sm text-green-600 dark:text-green-300 break-inside-avoid">
                  • {p}
                </p>
              ))}
            </div>
            {health.passed.length > COLLAPSE_THRESHOLD && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 h-7 w-full text-xs text-green-600 hover:text-green-700"
                onClick={() => setShowAllPassed(!showAllPassed)}
              >
                {showAllPassed ? "收起" : `展开全部 ${health.passed.length} 项`}
                {showAllPassed ? <ChevronDown className="ml-1 h-3 w-3" /> : <ChevronRight className="ml-1 h-3 w-3" />}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
