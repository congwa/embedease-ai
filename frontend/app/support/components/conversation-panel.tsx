"use client";

import { useRouter } from "next/navigation";
import { User, Bot, Headphones, Circle, ChevronRight, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ConversationWithPreview, UserConversationGroup } from "@/stores/support-workbench-store";

interface ConversationPanelProps {
  group: UserConversationGroup | null;
}

// 状态配置
const stateConfig = {
  pending: { label: "等待接入", color: "bg-yellow-500", textColor: "text-yellow-600" },
  human: { label: "人工服务中", color: "bg-green-500", textColor: "text-green-600" },
  ai: { label: "AI 模式", color: "bg-zinc-400", textColor: "text-zinc-500" },
};

// 热度指示（简化版，用图标 + 数字）
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

// 会话卡片
function ConversationCard({ conversation }: { conversation: ConversationWithPreview }) {
  const router = useRouter();
  const state = stateConfig[conversation.handoff_state as keyof typeof stateConfig] || stateConfig.ai;
  
  return (
    <div
      onClick={() => router.push(`/support/${conversation.id}`)}
      className={cn(
        "relative flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-all",
        "bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700",
        "hover:shadow-md hover:border-green-400 dark:hover:border-green-600",
        conversation.handoff_state === "pending" && "border-yellow-300 dark:border-yellow-700"
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
        
        {/* 最新消息预览 */}
        {conversation.lastMessage && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400 line-clamp-2 mb-2">
            {conversation.lastMessage}
          </p>
        )}
        
        <div className="flex items-center justify-between text-xs text-zinc-500">
          <div className="flex items-center gap-1">
            {conversation.handoff_state === "human" ? (
              <Headphones className="h-3 w-3" />
            ) : (
              <Bot className="h-3 w-3" />
            )}
            <span>{conversation.handoff_operator || "AI"}</span>
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
