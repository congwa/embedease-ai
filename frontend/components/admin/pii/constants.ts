// PII 预设规则和常量

export type PIIStrategy = "block" | "redact" | "mask" | "hash";

// 内置 PII 类型
export const BUILTIN_PII_TYPES = [
  "email",
  "credit_card",
  "ip",
  "mac_address",
  "url",
] as const;

// 预设规则模板
export const PII_PRESETS = [
  { type: "email", label: "📧 邮箱地址", detector: null, builtin: true },
  { type: "credit_card", label: "💳 信用卡号", detector: null, builtin: true },
  { type: "ip", label: "🌐 IP 地址", detector: null, builtin: true },
  { type: "mac_address", label: "🔗 MAC 地址", detector: null, builtin: true },
  { type: "url", label: "🔗 URL 链接", detector: null, builtin: true },
  // 中国特色
  { type: "phone_cn", label: "📱 手机号(中国)", detector: "1[3-9]\\d{9}", builtin: false },
  { type: "id_card_cn", label: "🪪 身份证号(中国)", detector: "\\d{17}[\\dXx]", builtin: false },
] as const;

// 策略选项
export const STRATEGY_OPTIONS: { value: PIIStrategy; label: string; icon: string; desc: string }[] = [
  { value: "block", label: "阻断", icon: "🚫", desc: "检测到 PII 时阻止请求" },
  { value: "redact", label: "脱敏", icon: "🔒", desc: "替换为 [REDACTED_TYPE]" },
  { value: "mask", label: "掩码", icon: "🎭", desc: "部分遮盖如 ****1234" },
  { value: "hash", label: "哈希", icon: "#️⃣", desc: "替换为哈希值" },
];

// 获取策略显示信息
export function getStrategyInfo(strategy: PIIStrategy) {
  return STRATEGY_OPTIONS.find((s) => s.value === strategy) || STRATEGY_OPTIONS[1];
}

// 获取 PII 类型的显示标签
export function getPIITypeLabel(type: string): string {
  const preset = PII_PRESETS.find((p) => p.type === type);
  return preset?.label || type;
}

// 判断是否为内置类型
export function isBuiltinType(type: string): boolean {
  return BUILTIN_PII_TYPES.includes(type as typeof BUILTIN_PII_TYPES[number]);
}
