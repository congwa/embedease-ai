/** Compact, read-only complaint context helps staff take over without obscuring the conversation. */
import { ClipboardList, ShieldCheck, Sparkles } from "lucide-react";
import { getSupportAgentLabel } from "../lib/agent-labels";
import { Button } from "@/components/ui/button";
import type {
  RecentTaskStateSummary,
  ReviewStateSummary,
  SecondaryIssueStateSummary,
  TicketStateSummary,
} from "@/types/websocket";
import {
  getComplaintReviewStatusLabel,
  getComplaintTaskStatusLabel,
  getComplaintTaskTypeLabel,
  getComplaintTicketStatusLabel,
} from "@/lib/config/complaint-ticket-flow";

interface ComplaintWorkbenchPanelProps {
  currentTicket: TicketStateSummary | null;
  reviewSummary: ReviewStateSummary | null;
  handoffReason: string | null;
  recentTasks: RecentTaskStateSummary[];
  secondaryIssues: SecondaryIssueStateSummary[];
  handoffSummary: Record<string, unknown> | null;
  ticketActionLoading?: "resolve" | "reopen" | null;
  onResolveTicket?: () => void;
  onReopenTicket?: () => void;
}

/** Dynamic summary values remain readable; no backend fields are assumed or fabricated. */
function summaryText(value: unknown): string {
  if (value == null || value === "") return "未提供";
  if (Array.isArray(value)) return value.map(summaryText).join(" / ");
  return typeof value === "object"
    ? JSON.stringify(value, null, 2)
    : String(value);
}

/** Translate standard severity codes while preserving unknown future values. */
function levelLabel(value?: string | null) {
  return (
    ({ high: "高", medium: "中", low: "低" } as Record<string, string>)[
      value ?? ""
    ] ??
    value ??
    "未评估"
  );
}

/** Current ticket, audit and handoff summary occupy distinct, vertically readable sections. */
export function ComplaintWorkbenchPanel({
  currentTicket,
  reviewSummary,
  handoffReason,
  recentTasks,
  secondaryIssues,
  handoffSummary,
  ticketActionLoading = null,
  onResolveTicket,
  onReopenTicket,
}: ComplaintWorkbenchPanelProps) {
  const canReopen =
    currentTicket && ["resolved", "closed"].includes(currentTicket.status);
  return (
    <div className="space-y-5 pt-4 text-sm">
      <section className="border-b border-border pb-5">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 text-xs font-semibold">
            <ClipboardList className="size-3.5" aria-hidden="true" />
            当前问题单
          </h3>
          {currentTicket && (
            <span
              className="text-[11px] text-muted-foreground"
              title={currentTicket.id}
            >
              #{currentTicket.id.slice(0, 8)}
            </span>
          )}
        </div>
        {currentTicket ? (
          <>
            <p className="mb-3 font-medium leading-6">
              {currentTicket.primary_issue_tag || "待识别问题"}
            </p>
            <div className="mb-5 flex flex-wrap gap-1.5">
              <span className="support-badge bg-secondary text-foreground">
                {getComplaintTicketStatusLabel(currentTicket.status)}
              </span>
              <span
                className={`support-badge ${currentTicket.risk_level === "high" ? "support-danger" : "support-warning"}`}
              >
                {levelLabel(currentTicket.risk_level)}风险
              </span>
            </div>
            <dl className="space-y-3 text-xs">
              {[
                [
                  "责任岗位",
                  getSupportAgentLabel(currentTicket.current_agent_tag),
                ],
                ["优先级", levelLabel(currentTicket.priority_level)],
                ["未解决轮次", String(currentTicket.unresolved_turns ?? 0)],
                ["要求人工", currentTicket.handoff_required ? "是" : "否"],
              ].map(([label, value]) => (
                <div className="flex justify-between gap-4" key={label}>
                  <dt className="shrink-0 text-muted-foreground">{label}</dt>
                  <dd className="text-right leading-5">{value}</dd>
                </div>
              ))}
              {currentTicket.updated_at && (
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">最近刷新</dt>
                  <dd className="text-right">
                    {new Date(currentTicket.updated_at).toLocaleString(
                      "zh-CN",
                      {
                        month: "numeric",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      },
                    )}
                  </dd>
                </div>
              )}
            </dl>
            <Button
              className="mt-5 w-full rounded-full"
              variant="outline"
              size="sm"
              disabled={
                ticketActionLoading !== null ||
                !(canReopen ? onReopenTicket : onResolveTicket)
              }
              onClick={canReopen ? onReopenTicket : onResolveTicket}
            >
              {ticketActionLoading
                ? "处理中…"
                : canReopen
                  ? "重新打开问题单"
                  : "标记已解决"}
            </Button>
          </>
        ) : (
          <p className="text-xs leading-6 text-muted-foreground">
            当前会话尚未建立问题单。接入后可先了解客户诉求。
          </p>
        )}
      </section>
      <section className="border-b border-border pb-5">
        <h3 className="mb-4 flex items-center gap-2 text-xs font-semibold">
          <ShieldCheck className="size-3.5" aria-hidden="true" />
          质量审查
        </h3>
        {reviewSummary ? (
          <>
            <div className="flex items-center justify-between gap-3">
              <span
                className={`support-badge ${reviewSummary.status === "passed" ? "support-success" : "support-warning"}`}
              >
                {getComplaintReviewStatusLabel(reviewSummary.status)}
              </span>
              <span className="text-xs">
                {typeof reviewSummary.score === "number"
                  ? `${reviewSummary.score} 分`
                  : "尚未评分"}
              </span>
            </div>
            {reviewSummary.reasons?.map((reason, index) => (
              <p
                className="mt-3 text-xs leading-6 text-muted-foreground"
                key={index}
              >
                {reason}
              </p>
            ))}
            <p className="mt-3 text-xs leading-5 text-muted-foreground">
              风险：{levelLabel(reviewSummary.risk_level)} · 下一建议岗位：
              {reviewSummary.suggested_next_agent
                ? getSupportAgentLabel(reviewSummary.suggested_next_agent)
                : "无"}
            </p>
          </>
        ) : (
          <p className="text-xs text-muted-foreground">暂无审查结果</p>
        )}
      </section>
      {(handoffReason ||
        Object.keys(handoffSummary ?? {}).length > 0 ||
        secondaryIssues.length > 0) && (
        <section className="border-b border-border pb-5">
          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold">
            <Sparkles className="size-3.5" aria-hidden="true" />
            AI 交接摘要
          </h3>
          {handoffReason && (
            <p className="mb-3 text-xs leading-6 text-muted-foreground">
              {handoffReason}
            </p>
          )}
          <dl className="space-y-3">
            {Object.entries(handoffSummary ?? {}).map(([key, value]) => (
              <div
                key={key}
                className="rounded-2xl border border-border bg-secondary/60 p-3"
              >
                <dt className="mb-1 text-xs text-muted-foreground">
                  {(
                    {
                      user_request: "客户诉求",
                      current_progress: "当前进展",
                      suggested_action: "建议下一步",
                      summary: "处理摘要",
                      missing_information: "待补充信息",
                    } as Record<string, string>
                  )[key] ?? key.replaceAll("_", " ")}
                </dt>
                <dd className="whitespace-pre-wrap text-xs leading-6">
                  {summaryText(value)}
                </dd>
              </div>
            ))}
          </dl>
          {secondaryIssues.map((issue, index) => (
            <div
              key={index}
              className="mt-3 rounded-2xl border border-border p-3"
            >
              <p className="text-xs font-medium">
                次级诉求 · {issue.issue_tag || "待分类"}
              </p>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                {issue.reason || "消息中出现了额外诉求"}
              </p>
              {issue.raw_message && (
                <p className="mt-2 text-xs leading-6 text-muted-foreground">
                  原话：{issue.raw_message}
                </p>
              )}
            </div>
          ))}
        </section>
      )}
      {recentTasks.length > 0 && (
        <section>
          <h3 className="mb-3 text-xs font-semibold">最近任务链</h3>
          <div className="space-y-2">
            {recentTasks.map((task) => (
              <details
                key={task.id}
                className="rounded-2xl border border-border p-3"
              >
                <summary className="cursor-pointer text-xs leading-6">
                  {getComplaintTaskTypeLabel(task.task_type)} ·{" "}
                  {getComplaintTaskStatusLabel(task.status)}
                </summary>
                <div className="mt-3 space-y-2 text-xs leading-6 text-muted-foreground">
                  <p>{getSupportAgentLabel(task.agent_tag)}</p>
                  {task.goal && <p>{task.goal}</p>}
                  {task.business_summary && <p>{task.business_summary}</p>}
                  {task.failure_reason && (
                    <p className="text-destructive">
                      失败原因：{task.failure_reason}
                    </p>
                  )}
                  {task.review_required && (
                    <p>
                      需要审查 ·{" "}
                      {getComplaintReviewStatusLabel(task.review_status)}
                    </p>
                  )}
                  {(task.started_at || task.created_at) && (
                    <p>
                      {new Date(
                        task.started_at || task.created_at!,
                      ).toLocaleString("zh-CN")}
                    </p>
                  )}
                </div>
              </details>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
