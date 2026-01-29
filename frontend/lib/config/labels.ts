/**
 * 用户友好的标签映射配置
 * 将技术术语转换为用户可理解的中文描述
 */

import type { LucideIcon } from "lucide-react";
import {
  Search,
  Info,
  Scale,
  Filter,
  FolderTree,
  Star,
  ShoppingCart,
  Compass,
  MessageSquare,
  ListTodo,
  Brain,
  FileText,
  RotateCcw,
  Gauge,
  Eraser,
  Layers,
  Sparkles,
  Settings,
} from "lucide-react";

// ========== 工具类别 ==========

export interface ToolCategoryInfo {
  label: string;
  desc: string;
  icon: LucideIcon;
  tools?: { name: string; desc: string }[];
}

export const TOOL_CATEGORY_LABELS: Record<string, ToolCategoryInfo> = {
  search: {
    label: "搜索",
    desc: "在商品库中搜索匹配产品",
    icon: Search,
    tools: [
      { name: "search_products", desc: "搜索匹配的商品" },
      { name: "find_similar_products", desc: "查找相似商品" },
    ],
  },
  query: {
    label: "查询",
    desc: "获取商品详细信息（价格、规格、库存等）",
    icon: Info,
    tools: [{ name: "get_product_details", desc: "获取商品详情" }],
  },
  compare: {
    label: "对比",
    desc: "对比多个商品的参数差异",
    icon: Scale,
    tools: [{ name: "compare_products", desc: "对比商品差异" }],
  },
  filter: {
    label: "筛选",
    desc: "按价格、属性等条件筛选商品",
    icon: Filter,
    tools: [
      { name: "filter_by_price", desc: "按价格区间筛选" },
      { name: "list_products_by_attribute", desc: "按属性筛选" },
    ],
  },
  category: {
    label: "分类",
    desc: "按类目浏览和导航商品",
    icon: FolderTree,
    tools: [
      { name: "list_all_categories", desc: "列出所有类目" },
      { name: "get_category_overview", desc: "获取类目概览" },
      { name: "list_products_by_category", desc: "按类目列出商品" },
      { name: "suggest_related_categories", desc: "推荐相关类目" },
    ],
  },
  featured: {
    label: "精选",
    desc: "展示精选推荐商品",
    icon: Star,
    tools: [{ name: "list_featured_products", desc: "获取精选商品" }],
  },
  purchase: {
    label: "购买",
    desc: "获取商品购买链接和渠道",
    icon: ShoppingCart,
    tools: [{ name: "get_product_purchase_links", desc: "获取购买链接" }],
  },
  guide: {
    label: "引导",
    desc: "引导用户明确需求",
    icon: Compass,
    tools: [{ name: "guide_user", desc: "引导用户" }],
  },
  faq: {
    label: "FAQ",
    desc: "FAQ 知识库检索",
    icon: MessageSquare,
    tools: [{ name: "faq_search", desc: "搜索 FAQ 知识库" }],
  },
  kb: {
    label: "知识库",
    desc: "通用知识库检索",
    icon: FileText,
    tools: [{ name: "kb_search", desc: "搜索知识库" }],
  },
};

export function getToolCategoryLabel(category: string): ToolCategoryInfo {
  return (
    TOOL_CATEGORY_LABELS[category] || {
      label: category,
      desc: "",
      icon: Settings,
    }
  );
}

// ========== 聊天模式 ==========

export interface ModeInfo {
  label: string;
  desc: string;
}

export const MODE_LABELS: Record<string, ModeInfo> = {
  natural: { label: "自然模式", desc: "平衡准确性和自然度" },
  free: { label: "自由模式", desc: "更灵活的回答风格" },
  strict: { label: "严格模式", desc: "严格基于知识库回答" },
};

export function getModeLabel(mode: string): string {
  return MODE_LABELS[mode]?.label || mode;
}

// ========== 中间件配置 ==========

export interface MiddlewareInfo {
  label: string;
  desc: string;
  icon: LucideIcon;
}

export const MIDDLEWARE_LABELS: Record<string, MiddlewareInfo> = {
  todo_enabled: {
    label: "TODO 规划",
    desc: "自动拆解复杂任务为步骤",
    icon: ListTodo,
  },
  memory_enabled: {
    label: "记忆系统",
    desc: "记住用户偏好和历史",
    icon: Brain,
  },
  summarization_enabled: {
    label: "上下文压缩",
    desc: "压缩长对话保持上下文",
    icon: FileText,
  },
  tool_retry_enabled: {
    label: "工具重试",
    desc: "工具调用失败时自动重试",
    icon: RotateCcw,
  },
  tool_limit_enabled: {
    label: "工具限制",
    desc: "限制单次对话工具调用次数",
    icon: Gauge,
  },
  noise_filter_enabled: {
    label: "噪音过滤",
    desc: "过滤冗余信息提升质量",
    icon: Eraser,
  },
  sliding_window_enabled: {
    label: "滑动窗口",
    desc: "限制上下文长度节省 token",
    icon: Layers,
  },
};

export function getMiddlewareLabel(key: string): MiddlewareInfo {
  return (
    MIDDLEWARE_LABELS[key] || {
      label: key.replace(/_/g, " "),
      desc: "",
      icon: Settings,
    }
  );
}

// ========== 路由策略 ==========

export const ROUTING_POLICY_LABELS: Record<string, string> = {
  keyword: "关键词匹配",
  intent: "意图识别",
  hybrid: "混合模式",
};

export function getRoutingPolicyLabel(type: string): string {
  return ROUTING_POLICY_LABELS[type] || type;
}

// ========== Agent 类型 ==========

export const AGENT_TYPE_LABELS: Record<string, string> = {
  product: "商品推荐",
  faq: "FAQ 问答",
  kb: "知识库",
  custom: "自定义",
};

export function getAgentTypeLabel(type: string): string {
  return AGENT_TYPE_LABELS[type] || type;
}

// ========== 运行态配置预览 - 工具名称 ==========

export interface ToolInfo {
  label: string;
  desc: string;
}

export const TOOL_NAME_LABELS: Record<string, ToolInfo> = {
  // 搜索类
  search_products: { label: "商品搜索", desc: "根据关键词搜索匹配的商品" },
  find_similar_products: { label: "相似商品", desc: "查找与指定商品相似的产品" },
  // 查询类
  get_product_details: { label: "商品详情", desc: "获取商品的详细信息" },
  // 对比类
  compare_products: { label: "商品对比", desc: "对比多个商品的参数差异" },
  // 筛选类
  filter_by_price: { label: "价格筛选", desc: "按价格区间筛选商品" },
  list_products_by_attribute: { label: "属性筛选", desc: "按商品属性筛选" },
  // 分类类
  list_all_categories: { label: "全部分类", desc: "列出所有商品类目" },
  get_category_overview: { label: "分类概览", desc: "获取类目的统计概览" },
  list_products_by_category: { label: "分类商品", desc: "列出某分类下的商品" },
  suggest_related_categories: { label: "相关分类", desc: "推荐相关的商品类目" },
  // 精选类
  list_featured_products: { label: "精选商品", desc: "获取精选推荐商品列表" },
  // 购买类
  get_product_purchase_links: { label: "购买链接", desc: "获取商品的购买渠道" },
  // 引导类
  guide_user: { label: "用户引导", desc: "引导用户明确购买需求" },
  // 知识库类
  faq_search: { label: "FAQ 搜索", desc: "搜索 FAQ 知识库" },
  kb_search: { label: "知识库搜索", desc: "搜索通用知识库" },
};

export function getToolNameLabel(name: string): ToolInfo {
  return TOOL_NAME_LABELS[name] || { label: name, desc: "" };
}

// ========== 运行态配置预览 - 中间件名称 ==========

export interface MiddlewarePipelineInfo {
  label: string;
  desc: string;
  icon?: LucideIcon;
}

export const MIDDLEWARE_PIPELINE_LABELS: Record<string, MiddlewarePipelineInfo> = {
  MemoryOrchestration: { label: "记忆编排", desc: "用户记忆的读取和写入", icon: Brain },
  ResponseSanitization: { label: "响应净化", desc: "过滤敏感内容和异常响应", icon: Eraser },
  SSE: { label: "流式输出", desc: "实时流式输出响应内容", icon: Sparkles },
  TodoList: { label: "任务规划", desc: "自动拆解复杂任务为步骤", icon: ListTodo },
  SequentialToolExecution: { label: "顺序执行", desc: "按顺序执行工具调用", icon: Layers },
  NoiseFilter: { label: "噪音过滤", desc: "过滤冗余信息提升质量", icon: Eraser },
  Logging: { label: "日志记录", desc: "记录请求和响应日志", icon: FileText },
  ToolRetry: { label: "工具重试", desc: "工具调用失败时自动重试", icon: RotateCcw },
  ToolCallLimit: { label: "调用限制", desc: "限制单次对话工具调用次数", icon: Gauge },
  SlidingWindow: { label: "滑动窗口", desc: "限制上下文长度节省 token", icon: Layers },
  Summarization: { label: "上下文压缩", desc: "压缩长对话保持上下文", icon: FileText },
  StrictMode: { label: "严格模式", desc: "严格基于工具返回内容回答", icon: Gauge },
};

export function getMiddlewarePipelineLabel(name: string): MiddlewarePipelineInfo {
  return MIDDLEWARE_PIPELINE_LABELS[name] || { label: name, desc: "" };
}

// ========== 运行态配置预览 - 提示词层级 ==========

export interface PromptLayerInfo {
  label: string;
  desc: string;
}

export const PROMPT_LAYER_LABELS: Record<string, PromptLayerInfo> = {
  base: { label: "基础提示词", desc: "Agent 的核心系统提示词" },
  mode_suffix: { label: "模式后缀", desc: "根据回答模式追加的指令" },
  skill_injection: { label: "技能注入", desc: "始终生效技能的内容注入" },
};

export function getPromptLayerLabel(name: string): PromptLayerInfo {
  return PROMPT_LAYER_LABELS[name] || { label: name, desc: "" };
}

// ========== 运行态配置预览 - 策略配置项 ==========

export interface PolicyFieldInfo {
  label: string;
  desc: string;
}

export const POLICY_FIELD_LABELS: Record<string, PolicyFieldInfo> = {
  // 工具策略
  min_tool_calls: { label: "最小调用次数", desc: "每次对话至少调用工具的次数" },
  allow_direct_answer: { label: "允许直接回答", desc: "是否允许不调用工具直接回答" },
  fallback_tool: { label: "兜底工具", desc: "无匹配时使用的默认工具" },
  clarification_tool: { label: "澄清工具", desc: "需要澄清时使用的工具" },
  // 中间件开关
  todo_enabled: { label: "任务规划", desc: "自动拆解复杂任务" },
  memory_enabled: { label: "记忆系统", desc: "记住用户偏好和历史" },
  sliding_window_enabled: { label: "滑动窗口", desc: "限制上下文长度" },
  summarization_enabled: { label: "上下文压缩", desc: "压缩长对话" },
  noise_filter_enabled: { label: "噪音过滤", desc: "过滤冗余信息" },
  tool_retry_enabled: { label: "工具重试", desc: "失败时自动重试" },
  strict_mode_enabled: { label: "严格模式", desc: "严格基于工具回答" },
};

export function getPolicyFieldLabel(field: string): PolicyFieldInfo {
  return POLICY_FIELD_LABELS[field] || { label: field.replace(/_/g, " "), desc: "" };
}

// ========== 运行态配置预览 - 配置来源 ==========

export const CONFIG_SOURCE_LABELS: Record<string, string> = {
  agent: "Agent 配置",
  settings: "全局设置",
  default: "系统默认",
  mode: "回答模式",
};

export function getConfigSourceLabel(source: string): string {
  return CONFIG_SOURCE_LABELS[source] || source;
}

// ========== 运行态配置预览 - 知识源类型 ==========

export const KNOWLEDGE_TYPE_LABELS: Record<string, string> = {
  faq: "FAQ 问答库",
  vector: "向量知识库",
  graph: "图谱知识库",
  product: "商品库",
  http_api: "外部 API",
  mixed: "混合知识源",
};

export function getKnowledgeTypeLabel(type: string): string {
  return KNOWLEDGE_TYPE_LABELS[type] || type;
}
