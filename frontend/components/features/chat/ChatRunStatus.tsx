"use client";

/** Keep a visible activity row throughout a chat turn, including the gap before its first token. */
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import type { TimelineState } from "@/lib/timeline";

/** Derive customer-facing progress from the current turn without depending on rendered reply text. */
export function getChatRunPhase(state: TimelineState, isStreaming: boolean): string | null {
  const { turnId } = state.activeTurn;
  if (!isStreaming || !state.activeTurn.isStreaming || !turnId) return null;

  const items = state.timeline.filter((item) => item.turnId === turnId);
  if (items.some((item) => item.type === "error" || item.type === "final")) return null;

  const tool = items.findLast((item) => item.type === "tool.call" && item.status === "running");
  if (tool?.type === "tool.call") {
    return /search|retriev|lookup|查询|检索|搜索/i.test(`${tool.name} ${tool.label}`)
      ? "正在查询相关资料…"
      : "正在处理请求…";
  }

  const calls = items.filter((item) => item.type === "llm.call.cluster");
  if (calls.some((item) => item.children.some((child) => child.type === "content" && child.text.trim()))) {
    return "正在回复…";
  }
  if (calls.length > 0) return "正在准备回复…";
  if (items.some((item) => item.type === "complaint.event")) return "正在处理请求…";
  return "正在发送请求…";
}

/** Mount once per active run so model/tool transitions and server message IDs do not reset the clock. */
function ActiveRunStatus({ phase }: { phase: string }) {
  const [startedAt] = useState(() => Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [startedAt]);

  return (
    <div className="mx-auto flex w-full max-w-3xl items-start gap-3 px-6 py-3 text-sm text-zinc-600 dark:text-zinc-400">
      <Loader2 aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 animate-spin motion-reduce:animate-none" />
      <div className="min-w-0 flex-1">
        <p role="status" aria-live="polite" aria-atomic="true">{phase}</p>
        {elapsed >= 30 && phase !== "正在回复…" && (
          <p role="status" className="mt-1 text-xs">等待时间较长，可以停止后重试。</p>
        )}
      </div>
      {/* Keep the ticking clock outside live regions to avoid announcing every second. */}
      <span aria-hidden="true" className="shrink-0 text-xs tabular-nums">
        {phase === "正在回复…" ? "已用时" : "已等待"} {elapsed} 秒
      </span>
    </div>
  );
}

/** End, abort and error states unmount the clock and remove the activity row. */
export function ChatRunStatus({ state, isStreaming }: { state: TimelineState; isStreaming: boolean }) {
  const phase = getChatRunPhase(state, isStreaming);
  return phase ? <ActiveRunStatus phase={phase} /> : null;
}
