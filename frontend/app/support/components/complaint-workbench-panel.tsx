/**
 * 客诉工作台上下文面板
 *
 * 这个文件的业务职责，是把当前主问题单、最近任务链、最近审查结果、
 * 次级诉求和转人工摘要集中展示给人工客服，减少人工接手时的上下文切换成本。
 */

import { cn } from "@/lib/utils";
import type {
  RecentTaskStateSummary,
  ReviewStateSummary,
  SecondaryIssueStateSummary,
  TicketStateSummary,
} from "@/types/websocket";
import { ComplaintActivityFeed } from "@/app/support/components/complaint-activity-feed";

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

const TICKET_STATUS_LABELS: Record<string, string> = {
  new: "新建",
  triaged: "已分诊",
  planned: "已规划",
  in_progress: "执行中",
  pending_review: "待审查",
  rework_required: "待返工",
  blocked: "已阻塞",
  handoff_pending: "待人工接管",
  handed_off: "人工处理中",
  resolved: "已解决",
  closed: "已关闭",
};

const TASK_TYPE_LABELS: Record<string, string> = {
  triage: "分诊",
  plan: "规划",
  emotion: "安抚",
  faq: "规则解释",
  case_collect: "信息补齐",
  resolution: "方案执行",
  handoff: "转人工",
  review: "审查",
};

const TASK_STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  running: "执行中",
  waiting_review: "待审查",
  done: "已完成",
  failed: "失败",
  cancelled: "已取消",
  blocked: "阻塞",
};

const REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: "待审查",
  passed: "已通过",
  rejected: "已驳回",
  escalated: "升级人工",
};

/**
 * 规范化状态标签展示。
 *
 * 这个方法服务于工作台读屏效率，把内部状态码转成客服可直接理解的短标签。
 */
function getLabelFromMap(value: string | null | undefined, labelMap: Record<string, string>): string {
  if (!value) {
    return "未设置";
  }
  return labelMap[value] ?? value.replaceAll("_", " ");
}

/**
 * 格式化时间。
 *
 * 这个方法服务于人工客服快速判断“这条状态是多久前发生的”，避免直接阅读 ISO 字符串。
 */
function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "未记录";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * 格式化任意转人工摘要字段值。
 *
 * 这个方法服务于 handoff_summary 的通用渲染，因为摘要内容会随着不同问题场景动态变化。
 */
function formatSummaryValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => formatSummaryValue(item)).join(" / ");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  if (value === null || value === undefined || value === "") {
    return "未提供";
  }
  return String(value);
}

/**
 * 计算任务卡片状态样式。
 *
 * 这个方法服务于人工客服一眼看出任务是成功、等待还是失败。
 */
function getTaskStatusClassName(status: string): string {
  if (status === "done") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-200";
  }
  if (status === "running" || status === "waiting_review") {
    return "border-amber-500/30 bg-amber-500/10 text-amber-200";
  }
  if (status === "failed" || status === "blocked") {
    return "border-red-500/30 bg-red-500/10 text-red-200";
  }
  return "border-zinc-700 bg-zinc-900/80 text-zinc-300";
}

/**
 * 客诉工作台上下文面板组件。
 *
 * 这个组件承载人工接手所需的最小上下文集合，确保客服不用来回翻聊天记录判断当前处理进度。
 */
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
  if (
    !currentTicket &&
    !reviewSummary &&
    !handoffReason &&
    recentTasks.length === 0 &&
    secondaryIssues.length === 0 &&
    !handoffSummary
  ) {
    return null;
  }

  const summaryEntries = Object.entries(handoffSummary ?? {});
  const canReopenTicket = currentTicket?.status === "resolved" || currentTicket?.status === "closed";

  return (
    <div className="border-b border-zinc-800 bg-zinc-950/80 px-4 py-3">
      <div className="mx-auto flex max-w-5xl flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {currentTicket && (
            <>
              <span className="rounded-full bg-blue-500/15 px-2.5 py-1 text-blue-300">
                主问题 {currentTicket.primary_issue_tag || getLabelFromMap(currentTicket.status, TICKET_STATUS_LABELS)}
              </span>
              <span className="rounded-full bg-zinc-800 px-2.5 py-1 text-zinc-300">
                状态 {getLabelFromMap(currentTicket.status, TICKET_STATUS_LABELS)}
              </span>
              {currentTicket.risk_level && (
                <span className="rounded-full bg-red-500/15 px-2.5 py-1 text-red-300">
                  风险 {currentTicket.risk_level}
                </span>
              )}
              {currentTicket.priority_level && (
                <span className="rounded-full bg-amber-500/15 px-2.5 py-1 text-amber-300">
                  优先级 {currentTicket.priority_level}
                </span>
              )}
              <span className="rounded-full bg-zinc-800 px-2.5 py-1 text-zinc-300">
                未解决 {currentTicket.unresolved_turns ?? 0} 轮
              </span>
            </>
          )}
          {reviewSummary && (
            <span className="rounded-full bg-orange-500/15 px-2.5 py-1 text-orange-300">
              审查 {getLabelFromMap(reviewSummary.status, REVIEW_STATUS_LABELS)}
              {typeof reviewSummary.score === "number" ? ` ${reviewSummary.score}` : ""}
            </span>
          )}
          {secondaryIssues.length > 0 && (
            <span className="rounded-full bg-fuchsia-500/15 px-2.5 py-1 text-fuchsia-300">
              次级诉求 {secondaryIssues.length}
            </span>
          )}
          {handoffReason && (
            <span className="rounded-full bg-zinc-800 px-2.5 py-1 text-zinc-300">
              转人工原因 {handoffReason}
            </span>
          )}
        </div>

        <div className="grid gap-3 xl:grid-cols-[1.1fr_0.95fr_0.95fr]">
          {currentTicket && (
            <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-100">当前问题单</h3>
                  <p className="text-xs text-zinc-500">人工接手的主处理对象</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-zinc-800 px-2 py-1 text-[11px] text-zinc-300">
                    {currentTicket.id.slice(0, 8)}
                  </span>
                  {canReopenTicket ? (
                    <button
                      onClick={onReopenTicket}
                      disabled={!onReopenTicket || ticketActionLoading !== null}
                      className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] text-amber-200 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {ticketActionLoading === "reopen" ? "重开中..." : "重新打开"}
                    </button>
                  ) : (
                    <button
                      onClick={onResolveTicket}
                      disabled={!onResolveTicket || ticketActionLoading !== null}
                      className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {ticketActionLoading === "resolve" ? "处理中..." : "标记已解决"}
                    </button>
                  )}
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">主问题标签</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {currentTicket.primary_issue_tag || "待识别"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">责任岗位</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {currentTicket.current_agent_tag || "尚未分配"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">是否要求人工</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {currentTicket.handoff_required ? "是" : "否"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">最近刷新</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {formatDateTime(currentTicket.updated_at)}
                  </div>
                </div>
              </div>
            </section>
          )}

          {reviewSummary && (
            <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-zinc-100">最近审查</h3>
                <p className="text-xs text-zinc-500">解释为什么本轮被通过、驳回或升级</p>
              </div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-orange-500/15 px-2 py-1 text-[11px] text-orange-300">
                    {getLabelFromMap(reviewSummary.status, REVIEW_STATUS_LABELS)}
                  </span>
                  {typeof reviewSummary.score === "number" && (
                    <span className="rounded-full bg-zinc-800 px-2 py-1 text-[11px] text-zinc-300">
                      评分 {reviewSummary.score}
                    </span>
                  )}
                  {reviewSummary.risk_level && (
                    <span className="rounded-full bg-red-500/15 px-2 py-1 text-[11px] text-red-300">
                      风险 {reviewSummary.risk_level}
                    </span>
                  )}
                </div>

                {reviewSummary.reasons && reviewSummary.reasons.length > 0 && (
                  <div className="space-y-2">
                    {reviewSummary.reasons.slice(0, 3).map((reason, index) => (
                      <div key={`${reason}-${index}`} className="rounded-xl bg-zinc-950/80 px-3 py-2 text-sm text-zinc-200">
                        {reason}
                      </div>
                    ))}
                  </div>
                )}

                <div className="text-xs text-zinc-400">
                  下一建议岗位: {reviewSummary.suggested_next_agent || "无"}
                </div>
              </div>
            </section>
          )}

          {(secondaryIssues.length > 0 || handoffReason || summaryEntries.length > 0) && (
            <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
              <div className="mb-3">
                <h3 className="text-sm font-semibold text-zinc-100">接手上下文</h3>
                <p className="text-xs text-zinc-500">次级诉求与转人工摘要</p>
              </div>

              <div className="space-y-3">
                {handoffReason && (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-3">
                    <div className="text-[11px] uppercase tracking-wide text-zinc-500">转人工原因</div>
                    <div className="mt-1 text-sm text-zinc-100">{handoffReason}</div>
                  </div>
                )}

                {secondaryIssues.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-[11px] uppercase tracking-wide text-zinc-500">次级诉求</div>
                    {secondaryIssues.slice(0, 3).map((issue, index) => (
                      <div key={`${issue.issue_tag}-${index}`} className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/5 p-3">
                        <div className="text-sm font-medium text-fuchsia-200">
                          {issue.issue_tag || "secondary_issue"}
                        </div>
                        <div className="mt-1 text-xs text-zinc-300">
                          {issue.reason || "消息中出现了额外诉求"}
                        </div>
                        {issue.raw_message && (
                          <div className="mt-2 line-clamp-2 text-xs text-zinc-500">
                            原话: {issue.raw_message}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {summaryEntries.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-[11px] uppercase tracking-wide text-zinc-500">转人工摘要</div>
                    <div className="grid gap-2">
                      {summaryEntries.map(([key, value]) => (
                        <div key={key} className="rounded-xl border border-zinc-800 bg-zinc-950/80 px-3 py-2">
                          <div className="text-[11px] uppercase tracking-wide text-zinc-500">
                            {key.replaceAll("_", " ")}
                          </div>
                          <pre className="mt-1 whitespace-pre-wrap break-words text-xs text-zinc-200">
                            {formatSummaryValue(value)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

        <ComplaintActivityFeed
          currentTicket={currentTicket}
          reviewSummary={reviewSummary}
          handoffReason={handoffReason}
          recentTasks={recentTasks}
        />

        {recentTasks.length > 0 && (
          <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
            <div className="mb-3">
              <h3 className="text-sm font-semibold text-zinc-100">最近任务链</h3>
              <p className="text-xs text-zinc-500">展示 AI 最近已经执行到哪一步，是否卡在审查或转人工</p>
            </div>

            <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
              {recentTasks.map((task) => (
                <article
                  key={task.id}
                  className={cn(
                    "rounded-2xl border p-3 transition-colors",
                    getTaskStatusClassName(task.status)
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-white">
                        {getLabelFromMap(task.task_type, TASK_TYPE_LABELS)}
                      </div>
                      <div className="mt-1 text-xs text-white/70">{task.agent_tag}</div>
                    </div>
                    <span className="rounded-full bg-black/20 px-2 py-1 text-[11px] text-white/80">
                      {getLabelFromMap(task.status, TASK_STATUS_LABELS)}
                    </span>
                  </div>

                  {task.goal && (
                    <p className="mt-3 text-sm text-white/90">{task.goal}</p>
                  )}

                  {task.business_summary && (
                    <p className="mt-2 text-xs leading-5 text-white/70">{task.business_summary}</p>
                  )}

                  {task.failure_reason && (
                    <div className="mt-2 rounded-xl bg-black/20 px-2.5 py-2 text-xs text-red-100">
                      失败原因: {task.failure_reason}
                    </div>
                  )}

                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-white/60">
                    {task.review_required && (
                      <span className="rounded-full bg-black/20 px-2 py-1">
                        需审查
                      </span>
                    )}
                    {task.review_status && (
                      <span className="rounded-full bg-black/20 px-2 py-1">
                        审查 {task.review_status}
                      </span>
                    )}
                    <span className="rounded-full bg-black/20 px-2 py-1">
                      {formatDateTime(task.started_at || task.created_at)}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
