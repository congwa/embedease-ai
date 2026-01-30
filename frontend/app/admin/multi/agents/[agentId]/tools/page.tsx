"use client";

import { useParams } from "next/navigation";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import { ToolOverviewCard } from "@/components/admin/tools";

export default function MultiAgentToolsPage() {
  const params = useParams();
  const agentId = params.agentId as string;
  const { agent } = useAgentDetail({ agentId });

  if (!agent) return null;

  return <ToolOverviewCard agent={agent} variant="multi" />;
}
