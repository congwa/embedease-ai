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
