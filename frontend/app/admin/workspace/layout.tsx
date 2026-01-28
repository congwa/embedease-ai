"use client";

import { useEffect } from "react";
import { useModeStore, useAgentStore } from "@/stores";

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { fetchModeState } = useModeStore();
  const { fetchAgents } = useAgentStore();

  useEffect(() => {
    fetchModeState();
    fetchAgents();
  }, [fetchModeState, fetchAgents]);

  return <>{children}</>;
}
