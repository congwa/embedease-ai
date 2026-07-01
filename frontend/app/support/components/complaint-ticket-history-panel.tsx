/**
 * 客诉问题单历史面板
 *
 * 这个文件的业务职责，是让客服在同一会话里查看历史 ticket 列表并切换到任意一张问题单详情，
 * 避免人工只能围绕“当前主问题单”操作，导致历史上下文和已关闭问题不可追溯。
 */

import { cn } from "@/lib/utils";
import type { TicketDetail, TicketSummary } from "@/lib/api/support";
import { ComplaintTicketStatusFlow } from "@/app/support/components/complaint-ticket-status-flow";

interface ComplaintTicketHistoryPanelProps {
  tickets: TicketSummary[];
  activeTicketId?: string | null;
  selectedTicketId: string | null;
  selectedTicketDetail: TicketDetail | null;
  isLoading?: boolean;
  ticketActionLoading?: "resolve" | "reopen" | null;
  onSelectTicket?: (ticketId: string) => void;
  onResolveTicket?: (ticketId: string) => void;
  onReopenTicket?: (ticketId: string) => void;
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

/**
 * 把问题单状态码转换为客服可读标签。
 *
 * 这个方法服务于历史 ticket 列表和详情页统一展示，避免 UI 直接暴露内部状态码。
 */
function getTicketStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "未设置";
  }
  return TICKET_STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

/**
 * 格式化时间文本。
 *
 * 这个方法服务于客服快速判断 ticket 最新更新时间和时间线节点，不直接显示原始 ISO 字符串。
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
 * 把动态业务对象转成可读文本。
 *
 * 这个方法服务于 slot_data、timeline extra 等动态结构展示，避免客服看到 `[object Object]`。
 */
function formatDynamicValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map((item) => formatDynamicValue(item)).join(" / ");
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
 * 客诉问题单历史面板。
 *
 * 这个组件把“同一会话下的多张 ticket”做成可切换视图，方便人工区分当前主单、历史已结单和被替代的问题单。
 */
export function ComplaintTicketHistoryPanel({
  tickets,
  activeTicketId = null,
  selectedTicketId,
  selectedTicketDetail,
  isLoading = false,
  ticketActionLoading = null,
  onSelectTicket,
  onResolveTicket,
  onReopenTicket,
}: ComplaintTicketHistoryPanelProps) {
  if (tickets.length === 0 && !selectedTicketDetail && !isLoading) {
    return null;
  }

  const slotEntries = Object.entries(selectedTicketDetail?.slot_data ?? {});
  const latestReview = selectedTicketDetail?.latest_review;
  const canReopenSelectedTicket =
    selectedTicketDetail?.status === "resolved" || selectedTicketDetail?.status === "closed";

  return (
    <div className="border-b border-zinc-800 bg-zinc-950/60 px-4 py-3">
      <div className="mx-auto grid max-w-5xl gap-3 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">问题单历史</h3>
              <p className="text-xs text-zinc-500">按 ticket 维度追溯同一会话内的问题演变</p>
            </div>
            <span className="rounded-full bg-zinc-800 px-2 py-1 text-[11px] text-zinc-300">
              {tickets.length} 张
            </span>
          </div>

          <div className="space-y-2">
            {tickets.map((ticket) => {
              const isSelected = ticket.id === selectedTicketId;
              const isActiveTicket = ticket.id === activeTicketId;

              return (
                <button
                  key={ticket.id}
                  type="button"
                  onClick={() => onSelectTicket?.(ticket.id)}
                  className={cn(
                    "w-full rounded-2xl border p-3 text-left transition-colors",
                    isSelected
                      ? "border-blue-500/40 bg-blue-500/10"
                      : "border-zinc-800 bg-zinc-950/70 hover:border-zinc-700 hover:bg-zinc-900"
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-zinc-100">
                        {ticket.primary_issue_tag || "未识别主问题"}
                      </div>
                      <div className="mt-1 text-xs text-zinc-400">
                        {ticket.id.slice(0, 8)} · {formatDateTime(ticket.updated_at)}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {isActiveTicket && (
                        <span className="rounded-full bg-emerald-500/20 px-2 py-1 text-[11px] text-emerald-200">
                          当前主单
                        </span>
                      )}
                      {isSelected && (
                        <span className="rounded-full bg-blue-500/20 px-2 py-1 text-[11px] text-blue-200">
                          当前查看
                        </span>
                      )}
                      <span className="rounded-full bg-zinc-800 px-2 py-1 text-[11px] text-zinc-300">
                        {getTicketStatusLabel(ticket.status)}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-zinc-400">
                    {ticket.risk_level && (
                      <span className="rounded-full bg-red-500/10 px-2 py-1 text-red-200">
                        风险 {ticket.risk_level}
                      </span>
                    )}
                    {ticket.priority_level && (
                      <span className="rounded-full bg-amber-500/10 px-2 py-1 text-amber-200">
                        优先级 {ticket.priority_level}
                      </span>
                    )}
                    <span className="rounded-full bg-zinc-800 px-2 py-1">
                      未解决 {ticket.unresolved_turns ?? 0} 轮
                    </span>
                    {ticket.secondary_issue_tags.length > 0 && (
                      <span className="rounded-full bg-fuchsia-500/10 px-2 py-1 text-fuchsia-200">
                        次级诉求 {ticket.secondary_issue_tags.length}
                      </span>
                    )}
                    {ticket.secondary_issue_detected && (
                      <span className="rounded-full bg-violet-500/10 px-2 py-1 text-violet-200">
                        本轮识别新诉求
                      </span>
                    )}
                    {ticket.merged_from_latest_message && (
                      <span className="rounded-full bg-sky-500/10 px-2 py-1 text-sky-200">
                        最近消息已归并
                      </span>
                    )}
                    {ticket.handoff_required && (
                      <span className="rounded-full bg-fuchsia-500/10 px-2 py-1 text-fuchsia-200">
                        需人工接手
                      </span>
                    )}
                  </div>
                </button>
              );
            })}

            {tickets.length === 0 && isLoading && (
              <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 px-3 py-6 text-center text-sm text-zinc-500">
                正在加载问题单列表...
              </div>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/70 p-4">
          <div className="mb-3 flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">问题单详情</h3>
              <p className="text-xs text-zinc-500">查看所选 ticket 的处理轨迹、槽位与审查结论</p>
            </div>
            {selectedTicketDetail && (
              <div className="flex items-center gap-2">
                {canReopenSelectedTicket ? (
                  <button
                    type="button"
                    onClick={() => onReopenTicket?.(selectedTicketDetail.id)}
                    disabled={!onReopenTicket || ticketActionLoading !== null}
                    className="rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] text-amber-200 transition-colors hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {ticketActionLoading === "reopen" ? "重开中..." : "重新打开"}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => onResolveTicket?.(selectedTicketDetail.id)}
                    disabled={!onResolveTicket || ticketActionLoading !== null}
                    className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-200 transition-colors hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {ticketActionLoading === "resolve" ? "处理中..." : "标记已解决"}
                  </button>
                )}
              </div>
            )}
          </div>

          {isLoading && !selectedTicketDetail ? (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 px-3 py-8 text-center text-sm text-zinc-500">
              正在加载问题单详情...
            </div>
          ) : !selectedTicketDetail ? (
            <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 px-3 py-8 text-center text-sm text-zinc-500">
              暂无可查看的问题单详情
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">主活动单</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {selectedTicketDetail.is_primary_active ? "是" : "否"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">状态</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {getTicketStatusLabel(selectedTicketDetail.status)}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">当前节点</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {selectedTicketDetail.current_node_key || "未记录"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">当前岗位</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {selectedTicketDetail.current_agent_tag || "未分配"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">风险</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {selectedTicketDetail.risk_level || "未设置"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">优先级</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {selectedTicketDetail.priority_level || "未设置"}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">返工次数</div>
                  <div className="mt-1 text-sm text-zinc-100">
                    {selectedTicketDetail.rework_count}
                  </div>
                </div>
              </div>

              {latestReview && (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
                  <div className="text-[11px] uppercase tracking-wide text-zinc-500">最近审查结论</div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-orange-500/15 px-2 py-1 text-[11px] text-orange-200">
                      {latestReview.status}
                    </span>
                    {typeof latestReview.score === "number" && (
                      <span className="rounded-full bg-zinc-800 px-2 py-1 text-[11px] text-zinc-300">
                        评分 {latestReview.score}
                      </span>
                    )}
                    {latestReview.risk_level && (
                      <span className="rounded-full bg-red-500/10 px-2 py-1 text-[11px] text-red-200">
                        风险 {latestReview.risk_level}
                      </span>
                    )}
                  </div>
                  {latestReview.reasons && latestReview.reasons.length > 0 && (
                    <div className="mt-2 space-y-2">
                      {latestReview.reasons.map((reason, index) => (
                        <div key={`${reason}-${index}`} className="rounded-xl bg-zinc-900 px-3 py-2 text-sm text-zinc-200">
                          {reason}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
                  <div className="mb-2 text-[11px] uppercase tracking-wide text-zinc-500">已收集槽位</div>
                  {slotEntries.length === 0 ? (
                    <div className="text-sm text-zinc-500">当前 ticket 尚未沉淀业务槽位</div>
                  ) : (
                    <div className="space-y-2">
                      {slotEntries.map(([key, value]) => (
                        <div key={key} className="rounded-xl bg-zinc-900 px-3 py-2">
                          <div className="text-[11px] uppercase tracking-wide text-zinc-500">
                            {key.replaceAll("_", " ")}
                          </div>
                          <pre className="mt-1 whitespace-pre-wrap break-words text-xs text-zinc-200">
                            {formatDynamicValue(value)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <ComplaintTicketStatusFlow ticket={selectedTicketDetail} />
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
                  <div className="mb-2 text-[11px] uppercase tracking-wide text-zinc-500">问题单关系</div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div>
                      <div className="text-[11px] uppercase tracking-wide text-zinc-500">父问题单</div>
                      <div className="mt-1 text-sm text-zinc-100">
                        {selectedTicketDetail.parent_ticket_id
                          ? selectedTicketDetail.parent_ticket_id.slice(0, 8)
                          : "无"}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] uppercase tracking-wide text-zinc-500">被替代为</div>
                      <div className="mt-1 text-sm text-zinc-100">
                        {selectedTicketDetail.superseded_by_ticket_id
                          ? selectedTicketDetail.superseded_by_ticket_id.slice(0, 8)
                          : "无"}
                      </div>
                    </div>
                    <div className="sm:col-span-2">
                      <div className="text-[11px] uppercase tracking-wide text-zinc-500">问题指纹</div>
                      <div className="mt-1 break-all text-sm text-zinc-100">
                        {selectedTicketDetail.issue_fingerprint || "未生成"}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-3">
                  <div className="mb-2 text-[11px] uppercase tracking-wide text-zinc-500">次级诉求记录</div>
                  {selectedTicketDetail.secondary_issues.length === 0 &&
                  selectedTicketDetail.secondary_issue_tags.length === 0 ? (
                    <div className="text-sm text-zinc-500">当前 ticket 暂无额外诉求记录</div>
                  ) : (
                    <div className="space-y-2">
                      {selectedTicketDetail.secondary_issues.map((issue, index) => (
                        <div
                          key={`${issue.issue_tag}-${index}`}
                          className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/5 px-3 py-2"
                        >
                          <div className="text-sm font-medium text-fuchsia-200">
                            {issue.issue_tag || "secondary_issue"}
                          </div>
                          <div className="mt-1 text-xs text-zinc-300">
                            {issue.reason || "消息中识别到了附带诉求"}
                          </div>
                          {issue.raw_message && (
                            <div className="mt-2 line-clamp-2 text-xs text-zinc-500">
                              原话: {issue.raw_message}
                            </div>
                          )}
                        </div>
                      ))}

                      {selectedTicketDetail.secondary_issues.length === 0 &&
                        selectedTicketDetail.secondary_issue_tags.map((issueTag) => (
                          <div
                            key={issueTag}
                            className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/5 px-3 py-2 text-sm text-fuchsia-200"
                          >
                            {issueTag}
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
