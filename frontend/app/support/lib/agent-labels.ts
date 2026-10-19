/** Human-readable role names keep implementation identifiers out of the primary support context. */
const roleLabels: Record<string, string> = {
  front_desk_agent: "前台分诊",
  service_planner_agent: "服务规划",
  emotion_deescalation_agent: "情绪安抚",
  case_intake_agent: "信息收集",
  faq_policy_agent: "规则解释",
  resolution_execution_agent: "问题处理推进",
  handoff_orchestrator_agent: "人工转接",
  quality_reviewer_agent: "质量审查",
  operations_patrol_agent: "服务巡检",
};

/** Unknown/custom roles remain identifiable without assuming a new backend vocabulary. */
export function getSupportAgentLabel(value?: string | null): string {
  return value ? (roleLabels[value] ?? value) : "等待分配";
}
