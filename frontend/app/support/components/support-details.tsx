"use client";

/** Shadcn tabs organize the existing ticket inspectors without inventing backend fields. */
import type { ReactNode } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface SupportDetailsProps {
  overview: ReactNode;
  history: ReactNode;
  activity: ReactNode;
}

/** The same inspector content works in the desktop column and accessible mobile sheet. */
export function SupportDetails({
  overview,
  history,
  activity,
}: SupportDetailsProps) {
  return (
    <Tabs
      defaultValue="overview"
      className="flex min-h-0 flex-1 flex-col gap-0"
    >
      <div className="shrink-0 px-4 pt-4 pb-2">
        <TabsList className="grid h-9 w-full grid-cols-2 rounded-xl bg-muted">
          <TabsTrigger value="overview" className="rounded-lg text-xs">
            问题概览
          </TabsTrigger>
          <TabsTrigger value="history" className="rounded-lg text-xs">
            处理记录
          </TabsTrigger>
        </TabsList>
      </div>
      <TabsContent
        value="overview"
        className="support-inspector m-0 min-h-0 flex-1 overflow-y-auto px-4 pb-5"
      >
        <div className="space-y-5">{overview}</div>
      </TabsContent>
      <TabsContent
        value="history"
        className="support-inspector m-0 min-h-0 flex-1 overflow-y-auto px-4 pb-5"
      >
        <div className="space-y-5">
          {activity}
          {history}
        </div>
      </TabsContent>
    </Tabs>
  );
}
