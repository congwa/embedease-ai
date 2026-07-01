/**
 * 客诉问题单状态流配置
 *
 * 这个文件的业务职责，是把问题单状态、时间线事件、任务类型和审查状态统一翻译成
 * 客服工作台可直接展示的中文标签与视觉语义，避免多个组件各自维护一套映射。
 */

export type ComplaintFlowTone = "neutral" | "info" | "success" | "warning" | "danger";

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
  review: "质量审查",
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

const TIMELINE_EVENT_META: Record<string, { label: string; tone: ComplaintFlowTone }> = {
  "triage.completed": { label: "完成分诊", tone: "info" },
  "plan.completed": { label: "完成规划", tone: "info" },
  "ticket.reopened": { label: "问题单已重开", tone: "warning" },
  "support.ticket.resolved": { label: "人工确认已解决", tone: "success" },
};

/**
 * 获取问题单状态中文标签。
 *
 * 这个方法服务于客服工作台的工单状态展示，避免直接暴露内部状态码。
 */
export function getComplaintTicketStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "未设置";
  }
  return TICKET_STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

/**
 * 获取任务类型中文标签。
 *
 * 这个方法服务于人工理解当前 AI 岗位到底在执行哪类动作，例如分诊、规划、方案执行。
 */
export function getComplaintTaskTypeLabel(taskType: string | null | undefined): string {
  if (!taskType) {
    return "未命名任务";
  }
  return TASK_TYPE_LABELS[taskType] ?? taskType.replaceAll("_", " ");
}

/**
 * 获取任务状态中文标签。
 *
 * 这个方法服务于客服在状态流中快速识别任务是运行中、已完成还是失败阻塞。
 */
export function getComplaintTaskStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "未设置";
  }
  return TASK_STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

/**
 * 获取审查状态中文标签。
 *
 * 这个方法服务于客服理解最近一次 review 的结论，而不是阅读英文枚举。
 */
export function getComplaintReviewStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "未设置";
  }
  return REVIEW_STATUS_LABELS[status] ?? status.replaceAll("_", " ");
}

/**
 * 获取时间线事件的展示标签与语义色。
 *
 * 这个方法服务于 ticket.timeline 的阶段渲染，把后端事件类型变成客服可理解的业务节点。
 */
export function getComplaintTimelineEventMeta(eventType: string | null | undefined): {
  label: string;
  tone: ComplaintFlowTone;
} {
  if (!eventType) {
    return { label: "状态更新", tone: "neutral" };
  }
  return TIMELINE_EVENT_META[eventType] ?? {
    label: eventType.replaceAll(".", " / ").replaceAll("_", " "),
    tone: "neutral",
  };
}
