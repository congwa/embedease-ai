/**
 * 客服会话分组详情面板
 *
 * 这个文件的业务职责，是在选中某个用户后，以会话卡片方式展示该用户的多张历史会话，
 * 并突出当前最需要人工优先处理的会话。
 */

"use client";

import { useRouter } from "next/navigation";
import { User, Bot, Headphones, Circle, ChevronRight, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ConversationWithPreview, UserConversationGroup } from "@/stores/support-workbench-store";

interface ConversationPanelProps {
  group: UserConversationGroup | null;
}

/**
 * 会话服务状态映射。
 *
 * 这个常量服务于把 handoff 状态转换成列表页可理解的队列标签。
 */
const stateConfig = {
  pending: { label: "等待接入", color: "bg-yellow-500", textColor: "text-yellow-600" },
  human: { label: "人工服务中", color: "bg-green-500", textColor: "text-green-600" },
  ai: { label: "AI 模式", color: "bg-zinc-400", textColor: "text-zinc-500" },
};

/**
 * 渲染热度指示。
 *
 * 这个方法服务于会话卡片，在列表页直接提示用户情绪热度和排队优先级。
 */
function HeatIndicator({ score }: { score: number }) {
  if (score < 20) return null;
  
  const config = 
    score >= 80 ? { color: "text-red-500", bg: "bg-red-500/10" } :
    score >= 60 ? { color: "text-orange-500", bg: "bg-orange-500/10" } :
    score >= 40 ? { color: "text-yellow-500", bg: "bg-yellow-500/10" } :
    { color: "text-zinc-400", bg: "bg-zinc-500/10" };
  
  return (
    <span className={cn("inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium", config.color, config.bg)}>
      🔥 {score}
    </span>
  );
}

/**
 * 获取风险标签样式。
 *
 * 这个方法服务于会话卡片，让人工快速识别高风险投诉单。
 */
function getRiskBadgeClass(riskLevel?: string | null) {
  if (riskLevel === "high") return "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300";
  if (riskLevel === "medium") return "bg-orange-100 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300";
  return "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300";
}

/**
 * 获取审查标签样式。
 *
 * 这个方法服务于会话卡片识别审查驳回、升级人工和已通过状态。
 */
function getReviewBadgeClass(reviewStatus?: string | null) {
  if (reviewStatus === "rejected") return "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300";
  if (reviewStatus === "escalated") return "bg-orange-100 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300";
  if (reviewStatus === "passed") return "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-300";
  return "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400";
}

/**
 * 获取问题单状态中文标签。
 *
 * 这个方法服务于会话卡片在列表页直接显示主问题单当前所处阶段。
 */
function getTicketStatusLabel(status?: string | null): string {
  if (!status) {
    return "未建单";
  }
  const labels: Record<string, string> = {
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
  return labels[status] ?? status.replaceAll("_", " ");
}

/**
 * 获取会话卡片边框强调样式。
 *
 * 这个方法服务于把待接入、高风险和返工中的会话在视觉上优先抬出来。
 */
function getConversationPriorityClass(conversation: ConversationWithPreview): string {
  if (conversation.handoff_state === "pending") {
    return "border-yellow-300 shadow-yellow-500/10 dark:border-yellow-700";
  }
  if (conversation.risk_level === "high") {
    return "border-red-300 shadow-red-500/10 dark:border-red-800";
  }
  if (conversation.review_status === "rejected" || conversation.ticket_status === "rework_required" || conversation.ticket_status === "blocked") {
    return "border-orange-300 shadow-orange-500/10 dark:border-orange-800";
  }
  return "border-zinc-200 dark:border-zinc-700";
}

/**
 * 渲染会话卡片。
 *
 * 这个组件服务于客服在单个用户下比较多张会话时，快速定位当前最值得优先处理的会话。
 */
function ConversationCard({ conversation }: { conversation: ConversationWithPreview }) {
  const router = useRouter();
  const state = stateConfig[conversation.handoff_state as keyof typeof stateConfig] || stateConfig.ai;
  
  return (
    <div
      onClick={() => router.push(`/support/${conversation.id}`)}
      className={cn(
        "relative flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-all",
        "bg-white dark:bg-zinc-800",
        "hover:shadow-md hover:border-green-400 dark:hover:border-green-600",
        getConversationPriorityClass(conversation)
      )}
    >
      {/* 未读指示 */}
      {conversation.unread_count > 0 && (
        <div className="absolute -top-1.5 -right-1.5">
          <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1.5 text-[10px] font-medium text-white">
            {conversation.unread_count > 99 ? "99+" : conversation.unread_count}
          </span>
        </div>
      )}

      {/* 左侧时间线节点 */}
      <div className="flex flex-col items-center">
        <div className={cn("h-3 w-3 rounded-full border-2 border-white dark:border-zinc-800", state.color)} />
      </div>

      {/* 会话信息 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-zinc-900 dark:text-zinc-100 truncate">
            {conversation.title || "新会话"}
          </span>
          <span className={cn("flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] text-white", state.color)}>
            <Circle className="h-1.5 w-1.5 fill-current" />
            {state.label}
          </span>
          <HeatIndicator score={conversation.heat_score} />
        </div>

        <div className="mb-2 flex flex-wrap items-center gap-1.5">
          {conversation.primary_issue_tag && (
            <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
              {conversation.primary_issue_tag}
            </span>
          )}
          {conversation.ticket_status && (
            <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200">
              {getTicketStatusLabel(conversation.ticket_status)}
            </span>
          )}
          {conversation.risk_level && (
            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", getRiskBadgeClass(conversation.risk_level))}>
              风险 {conversation.risk_level}
            </span>
          )}
          {conversation.review_status && (
            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", getReviewBadgeClass(conversation.review_status))}>
              审查 {conversation.review_status}
              {typeof conversation.review_score === "number" ? ` ${conversation.review_score}` : ""}
            </span>
          )}
          {conversation.secondary_issue_detected && (
            <span className="rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
              次级问题
            </span>
          )}
          {conversation.unread_count > 0 && (
            <span className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300">
              未读 {conversation.unread_count}
            </span>
          )}
        </div>
        
        {/* 最新消息预览 */}
        {conversation.lastMessage && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2 mb-2">
            {conversation.lastMessage}
          </p>
        )}

        {conversation.handoff_reason && conversation.handoff_state === "pending" && (
          <div className="mb-2 rounded-xl bg-amber-50 px-2.5 py-2 text-xs text-amber-700 dark:bg-amber-950/30 dark:text-amber-300">
            待接入原因: {conversation.handoff_reason}
          </div>
        )}
        
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <div className="flex items-center gap-1.5">
            {conversation.handoff_state === "human" ? (
              <Headphones className="h-3 w-3" />
            ) : (
              <Bot className="h-3 w-3" />
            )}
            <span>{conversation.handoff_operator || conversation.current_agent_tag || "AI"}</span>
          </div>
          <span>{new Date(conversation.updated_at).toLocaleString()}</span>
        </div>
      </div>

      {/* 进入箭头 */}
      <ChevronRight className="h-5 w-5 text-zinc-400 flex-shrink-0" />
    </div>
  );
}

export function ConversationPanel({ group }: ConversationPanelProps) {
  if (!group) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-zinc-500">
        <MessageSquare className="h-16 w-16 mb-4 opacity-30" />
        <p className="text-lg font-medium mb-1">选择用户查看会话</p>
        <p className="text-sm opacity-70">在左侧列表中点击用户</p>
      </div>
    );
  }

  const shortId = group.userId.slice(0, 8);

  return (
    <div className="h-full flex flex-col">
      {/* 用户信息头部 */}
      <div className="flex items-center gap-4 p-6 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="relative">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-zinc-100 dark:bg-zinc-700">
            <User className="h-7 w-7 text-zinc-500" />
          </div>
          {group.hasOnlineUser && (
            <span className="absolute bottom-0 right-0 h-4 w-4 rounded-full border-2 border-white bg-green-500 dark:border-zinc-900" />
          )}
        </div>
        <div>
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
            用户 {shortId}...
          </h2>
          <div className="flex items-center gap-3 text-sm text-zinc-500">
            <span>{group.conversations.length} 个会话</span>
            <span>•</span>
            <span>最高热度 {group.maxHeatScore}</span>
            {group.totalUnread > 0 && (
              <>
                <span>•</span>
                <span className="text-red-500">{group.totalUnread} 未读</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* 会话时间线 */}
      <div className="flex-1 overflow-auto p-6">
        <h3 className="text-sm font-medium text-zinc-500 mb-4">会话记录</h3>
        <div className="relative">
          {/* 时间线 */}
          <div className="absolute left-[22px] top-0 bottom-0 w-0.5 bg-zinc-200 dark:bg-zinc-700" />
          
          {/* 会话列表 */}
          <div className="space-y-4">
            {group.conversations.map((conv) => (
              <ConversationCard key={conv.id} conversation={conv} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
