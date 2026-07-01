/**
 * 客服工作台实时监控选取规则
 *
 * 这个文件的业务职责，是为客服列表页挑出“最值得持续占用 WebSocket 连接”的会话，
 * 让有限的实时订阅优先覆盖待接入、高风险、返工和高热队列。
 */

import type { ConversationWithPreview } from "@/stores/support-workbench-store";

const DEFAULT_MONITOR_LIMIT = 12;

/**
 * 计算会话的实时监控优先级。
 *
 * 这个方法服务于客服工作台在连接数有限时，优先订阅最可能影响排队判断的会话。
 */
function getConversationMonitorPriority(conversation: ConversationWithPreview): number {
  let score = 0;

  if (conversation.handoff_state === "pending") {
    score += 1000;
  } else if (conversation.handoff_state === "human") {
    score += 700;
  }

  if (conversation.risk_level === "high") {
    score += 500;
  } else if (conversation.risk_level === "medium") {
    score += 250;
  }

  if (
    conversation.review_status === "rejected" ||
    conversation.ticket_status === "rework_required" ||
    conversation.ticket_status === "blocked"
  ) {
    score += 350;
  }

  if (
    conversation.ticket_status &&
    conversation.ticket_status !== "resolved" &&
    conversation.ticket_status !== "closed"
  ) {
    score += 180;
  }

  score += Math.min(conversation.unread_count ?? 0, 20) * 15;
  score += Math.min(conversation.heat_score ?? 0, 100);

  if (conversation.user_online) {
    score += 80;
  }

  const agePenaltyMinutes = Math.floor(
    (Date.now() - new Date(conversation.updated_at).getTime()) / 60000
  );
  score -= Math.min(Math.max(agePenaltyMinutes, 0), 240);

  return score;
}

/**
 * 生成客服列表页需要建立实时订阅的会话集合。
 *
 * 这个方法保证当前选中用户组始终在线，同时把剩余额度留给全局最重要的会话。
 */
export function buildSupportWorkbenchMonitoredConversations(
  conversations: ConversationWithPreview[],
  selectedConversations: ConversationWithPreview[] = [],
  limit = DEFAULT_MONITOR_LIMIT
): ConversationWithPreview[] {
  const selectedIds = new Set(selectedConversations.map((conversation) => conversation.id));
  const prioritizedOthers = conversations
    .filter((conversation) => !selectedIds.has(conversation.id))
    .sort((left, right) => {
      const priorityDiff =
        getConversationMonitorPriority(right) - getConversationMonitorPriority(left);
      if (priorityDiff !== 0) {
        return priorityDiff;
      }
      return (
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
      );
    });

  return [
    ...selectedConversations,
    ...prioritizedOthers.slice(0, Math.max(limit - selectedConversations.length, 0)),
  ];
}

