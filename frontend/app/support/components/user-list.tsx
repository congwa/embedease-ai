"use client";

/** Real customer groups retain access to every historical conversation inside the compact inbox. */
import { Flame, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserConversationGroup } from "@/stores/support-workbench-store";

interface UserListProps {
  groups: UserConversationGroup[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
}

/** Relative timestamps keep recent queue activity readable without hiding the full timestamp. */
function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "未记录";
  const minutes = Math.max(
    0,
    Math.floor((Date.now() - date.getTime()) / 60000),
  );
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`;
  return date.toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
}

/** Each conversation is a keyboard-operable row, grouped by the backend user identity. */
export function UserList({
  groups,
  activeConversationId,
  onSelectConversation,
}: UserListProps) {
  return (
    <div className="space-y-2">
      {groups.map((group) => (
        <section key={group.userId} aria-label={`客户 ${group.userId}`}>
          {group.conversations.length > 1 && (
            <p className="px-3 pt-2 pb-1 text-xs text-muted-foreground">
              客户 {group.userId.slice(0, 8)} · {group.conversations.length}{" "}
              个会话
            </p>
          )}
          {group.conversations.map((conversation) => {
            const selected = activeConversationId === conversation.id;
            const status = conversation.handoff_state;
            return (
              <button
                key={conversation.id}
                aria-current={selected ? "page" : undefined}
                onClick={() => onSelectConversation(conversation.id)}
                className={cn("support-queue-row", selected && "is-selected")}
              >
                <span className="relative mt-1 flex size-9 shrink-0 items-center justify-center rounded-xl bg-secondary text-muted-foreground">
                  <UserRound className="size-4" aria-hidden="true" />
                  {conversation.user_online && (
                    <span className="absolute -right-0.5 -bottom-0.5 size-2 rounded-full border-2 border-card bg-emerald-300" />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-start justify-between gap-2">
                    <span className="truncate text-sm font-medium">
                      客户 {group.userId.slice(0, 8)}
                    </span>
                    <time
                      className="mt-0.5 shrink-0 text-[11px] text-muted-foreground"
                      dateTime={conversation.updated_at}
                      title={new Date(conversation.updated_at).toLocaleString()}
                    >
                      {formatTime(conversation.updated_at)}
                    </time>
                  </span>
                  <span
                    className="mt-1 block truncate text-xs leading-5 text-muted-foreground"
                    title={conversation.title}
                  >
                    {conversation.title || conversation.lastMessage || "新会话"}
                  </span>
                  {conversation.lastMessage && (
                    <span
                      className="mt-0.5 block truncate text-xs text-muted-foreground"
                      title={conversation.lastMessage}
                    >
                      {conversation.lastMessage}
                    </span>
                  )}
                  <span className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span
                      className={cn(
                        "support-badge",
                        status === "pending"
                          ? "support-warning"
                          : status === "human"
                            ? "support-success"
                            : "bg-secondary text-muted-foreground",
                      )}
                    >
                      {status === "pending"
                        ? "待接入"
                        : status === "human"
                          ? "人工处理中"
                          : "AI 处理中"}
                    </span>
                    {conversation.heat_score >= 40 && (
                      <span className="inline-flex items-center gap-0.5 text-[11px] text-amber-200">
                        <Flame aria-hidden="true" className="size-3" />
                        {conversation.heat_score}
                      </span>
                    )}
                    {conversation.risk_level === "high" && (
                      <span className="support-badge support-danger">
                        高风险
                      </span>
                    )}
                    {(conversation.review_status === "rejected" ||
                      ["rework_required", "blocked"].includes(
                        conversation.ticket_status ?? "",
                      )) && (
                      <span className="support-badge support-warning">
                        返工/阻塞
                      </span>
                    )}
                    {conversation.unread_count > 0 && (
                      <span
                        className="ml-auto flex min-w-4 items-center justify-center rounded bg-primary px-1 text-[10px] font-semibold text-primary-foreground"
                        aria-label={`${conversation.unread_count} 条未读`}
                      >
                        {conversation.unread_count > 99
                          ? "99+"
                          : conversation.unread_count}
                      </span>
                    )}
                  </span>
                </span>
              </button>
            );
          })}
        </section>
      ))}
    </div>
  );
}
