/**
 * 客服用户分组列表
 *
 * 这个文件的业务职责，是在用户维度展示客服当前待处理队列，并提前暴露待接入、
 * 高风险和返工信号，让人工先决定该点开哪位用户。
 */

"use client";

import { User, Flame } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserConversationGroup } from "@/stores/support-workbench-store";

interface UserListProps {
  groups: UserConversationGroup[];
  selectedUserId: string | null;
  onSelectUser: (userId: string) => void;
}

/**
 * 渲染热度指示器。
 *
 * 这个方法服务于客服快速识别当前用户组的情绪热度和处理紧急度。
 */
function HeatIndicator({ score }: { score: number }) {
  if (score < 40) return null;
  
  const color = score >= 80 ? "text-red-500" : score >= 60 ? "text-orange-500" : "text-yellow-500";
  
  return <Flame className={cn("h-3.5 w-3.5", color)} />;
}

/**
 * 渲染未读徽章。
 *
 * 这个方法服务于客服快速判断该用户组是否还有未处理消息。
 */
function UnreadBadge({ count }: { count: number }) {
  if (count === 0) return null;
  
  return (
    <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-medium text-white">
      {count > 99 ? "99+" : count}
    </span>
  );
}

/**
 * 渲染用户组当前优先状态。
 *
 * 这个方法服务于在列表页第一时间区分待接入、人工中和 AI 跟进中的用户组。
 */
function StateIndicator({ state }: { state: "pending" | "human" | "ai" }) {
  const config = {
    pending: { color: "bg-yellow-500", pulse: true },
    human: { color: "bg-green-500", pulse: false },
    ai: { color: "bg-zinc-400", pulse: false },
  };
  
  const { color, pulse } = config[state];
  
  return (
    <span className={cn("h-2.5 w-2.5 rounded-full", color, pulse && "animate-pulse")} />
  );
}

/**
 * 格式化时间。
 *
 * 这个方法服务于客服列表页，让人工快速判断该用户组最近何时发生过更新。
 */
function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return "刚刚";
  if (diffMins < 60) return `${diffMins}分钟前`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}小时前`;
  
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}天前`;
  
  return date.toLocaleDateString();
}

export function UserList({ groups, selectedUserId, onSelectUser }: UserListProps) {
  if (groups.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-12 text-zinc-500">
        <User className="h-10 w-10 mb-3 opacity-50" />
        <p className="text-sm">暂无用户</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {groups.map((group) => {
        const isSelected = selectedUserId === group.userId;
        const shortId = group.userId.slice(0, 8);
        
        return (
          <button
            key={group.userId}
            onClick={() => onSelectUser(group.userId)}
            className={cn(
              "flex items-center gap-3 px-4 py-3 text-left transition-colors border-b border-zinc-100 dark:border-zinc-800",
              "hover:bg-zinc-50 dark:hover:bg-zinc-800/50",
              isSelected && "bg-green-50 dark:bg-green-900/20 border-l-2 border-l-green-500"
            )}
          >
            {/* 用户头像 */}
            <div className="relative flex-shrink-0">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-700">
                <User className="h-5 w-5 text-zinc-500" />
              </div>
              {/* 在线状态 */}
              {group.hasOnlineUser && (
                <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white bg-green-500 dark:border-zinc-900" />
              )}
            </div>

            {/* 用户信息 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
                  {shortId}...
                </span>
                <HeatIndicator score={group.maxHeatScore} />
              </div>
              {/* 最新消息预览 */}
              {group.lastMessage ? (
                <p className="text-xs text-zinc-500 truncate mt-0.5">
                  {group.lastMessage}
                </p>
              ) : (
                <div className="flex items-center gap-2 mt-0.5">
                  <StateIndicator state={group.priorityState} />
                  <span className="text-xs text-zinc-500">
                    {group.conversations.length} 个会话
                  </span>
                </div>
              )}

              <div className="mt-1 flex flex-wrap gap-1">
                {group.pendingConversationCount > 0 && (
                  <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
                    待接入 {group.pendingConversationCount}
                  </span>
                )}
                {group.highRiskConversationCount > 0 && (
                  <span className="rounded-full bg-red-50 px-1.5 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">
                    高风险 {group.highRiskConversationCount}
                  </span>
                )}
                {group.reworkConversationCount > 0 && (
                  <span className="rounded-full bg-orange-50 px-1.5 py-0.5 text-[10px] font-medium text-orange-700 dark:bg-orange-950/40 dark:text-orange-300">
                    返工/阻塞 {group.reworkConversationCount}
                  </span>
                )}
              </div>
            </div>

            {/* 右侧信息 */}
            <div className="flex flex-col items-end gap-1 flex-shrink-0">
              <UnreadBadge count={group.totalUnread} />
              <span className="text-[10px] text-zinc-400">
                {formatTime(group.latestUpdate)}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
