/**
 * 导航菜单配置
 * 统一管理单 Agent 模式和多 Agent 模式的菜单配置
 */

import {
  LayoutDashboard,
  Bot,
  Settings,
  Wrench,
  BarChart3,
  Package,
  HelpCircle,
  Database,
  Network,
  Route,
  FileText,
  Globe,
  MessageSquare,
  MessageCircle,
  Users,
  Wand2,
  Sparkles,
  Layers,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  exact?: boolean;
  highlight?: boolean;
  highlightColor?: "emerald" | "violet" | "blue" | "orange";
  badge?: string;
  badgeVariant?: "default" | "secondary" | "outline";
  children?: Omit<NavItem, "icon" | "children">[];
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

export interface NavConfig {
  main: NavSection;
  workspace?: NavSection;
  system: NavSection;
  footer?: NavItem[];
}

/**
 * 是否在 Agent 控制台展示「商品数据」入口（全局商品库）
 *
 * 自定义助手也可维护/使用同一商品库，故与「商品推荐」类型一并展示。
 */
export function agentHasProductCatalogNav(agentType: string): boolean {
  return agentType === "product" || agentType === "custom";
}

/**
 * 单 Agent 模式 - 主菜单
 */
export const singleModeMainNav: NavItem[] = [
  {
    title: "仪表盘",
    href: "/admin",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    title: "Agent 配置",
    href: "/admin/single",
    icon: Bot,
    exact: true,
    highlight: true,
    highlightColor: "emerald",
  },
];

/**
 * 单 Agent 模式 - Agent 控制台菜单（根据当前 Agent 动态生成）
 */
export const getSingleAgentConsoleNav = (agentId: string, agentType: string): NavItem[] => {
  const baseItems: NavItem[] = [
    {
      title: "基础设置",
      href: `/admin/single/agents/${agentId}`,
      icon: Settings,
      exact: true,
    },
    {
      title: "工具配置",
      href: `/admin/single/agents/${agentId}/tools`,
      icon: Wrench,
      exact: true,
    },
    {
      title: "会话洞察",
      href: `/admin/single/agents/${agentId}/conversations`,
      icon: BarChart3,
      exact: true,
    },
  ];

  // 根据 Agent 类型添加特定菜单
  if (agentHasProductCatalogNav(agentType)) {
    baseItems.push({
      title: "商品数据",
      href: "/admin/products",
      icon: Package,
      exact: true,
    });
  }

  if (agentType === "faq") {
    baseItems.push({
      title: "FAQ 管理",
      href: `/admin/single/agents/${agentId}/faq`,
      icon: HelpCircle,
      exact: true,
    });
  }

  if (agentType === "kb" || agentType === "faq") {
    baseItems.push({
      title: "知识库",
      href: `/admin/single/agents/${agentId}/knowledge`,
      icon: Database,
      exact: true,
    });
  }

  return baseItems;
};

/**
 * 多 Agent 模式 - 主菜单
 */
export const multiModeMainNav: NavItem[] = [
  {
    title: "仪表盘",
    href: "/admin",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    title: "编排配置",
    href: "/admin/multi",
    icon: Network,
    exact: true,
    highlight: true,
    highlightColor: "violet",
  },
  {
    title: "路由策略",
    href: "/admin/multi/routing",
    icon: Route,
    exact: true,
  },
  {
    title: "子 Agent 管理",
    href: "/admin/multi/agents",
    icon: Bot,
  },
];

/**
 * 多 Agent 模式 - 子 Agent 控制台菜单
 */
export const getMultiAgentConsoleNav = (agentId: string, agentType: string): NavItem[] => {
  const baseItems: NavItem[] = [
    {
      title: "基础设置",
      href: `/admin/multi/agents/${agentId}`,
      icon: Settings,
      exact: true,
    },
    {
      title: "工具配置",
      href: `/admin/multi/agents/${agentId}/tools`,
      icon: Wrench,
      exact: true,
    },
    {
      title: "路由关键词",
      href: `/admin/multi/agents/${agentId}/routing`,
      icon: Route,
      exact: true,
    },
  ];

  if (agentHasProductCatalogNav(agentType)) {
    baseItems.push({
      title: "商品数据",
      href: "/admin/products",
      icon: Package,
      exact: true,
    });
  }

  if (agentType === "faq") {
    baseItems.push({
      title: "FAQ 管理",
      href: `/admin/multi/agents/${agentId}/faq`,
      icon: HelpCircle,
      exact: true,
    });
  }

  if (agentType === "kb" || agentType === "faq") {
    baseItems.push({
      title: "知识库",
      href: `/admin/multi/agents/${agentId}/knowledge`,
      icon: Database,
      exact: true,
    });
  }

  return baseItems;
};

/**
 * 系统管理菜单（两种模式共用）
 */
export const systemNavItems: NavItem[] = [
  {
    title: "Agent 中心",
    href: "/admin/agents",
    icon: Bot,
    exact: true,
  },
  {
    title: "技能管理",
    href: "/admin/skills",
    icon: Wand2,
    exact: true,
  },
  {
    title: "提示词管理",
    href: "/admin/prompts",
    icon: FileText,
    exact: true,
  },
  {
    title: "爬虫管理",
    href: "/admin/crawler",
    icon: Globe,
    children: [
      { title: "站点配置", href: "/admin/crawler/sites" },
      { title: "任务列表", href: "/admin/crawler/tasks" },
      { title: "页面数据", href: "/admin/crawler/pages" },
    ],
  },
  {
    title: "会话管理",
    href: "/admin/conversations",
    icon: MessageSquare,
    exact: true,
  },
  {
    title: "用户管理",
    href: "/admin/users",
    icon: Users,
    exact: true,
  },
  {
    title: "设置中心",
    href: "/admin/settings",
    icon: Settings,
    exact: true,
  },
];

/**
 * 单 Agent 模式 - 底部入口（配置多 Agent）
 */
export const singleModeFooterNav: NavItem[] = [
  {
    title: "测试聊天",
    href: "/chat",
    icon: MessageCircle,
    highlight: true,
    highlightColor: "blue",
  },
  {
    title: "快速配置",
    href: "/admin/quick-setup",
    icon: Sparkles,
  },
  {
    title: "配置编排模式",
    href: "/admin/multi",
    icon: Network,
    badge: "预设",
    badgeVariant: "outline",
    highlightColor: "violet",
  },
];

/**
 * 多 Agent 模式 - 底部入口（配置单 Agent）
 */
export const multiModeFooterNav: NavItem[] = [
  {
    title: "测试聊天",
    href: "/chat",
    icon: MessageCircle,
    highlight: true,
    highlightColor: "blue",
  },
  {
    title: "快速配置",
    href: "/admin/quick-setup",
    icon: Sparkles,
  },
  {
    title: "配置单 Agent 模式",
    href: "/admin/single",
    icon: Bot,
    badge: "预设",
    badgeVariant: "outline",
    highlightColor: "emerald",
  },
];

/**
 * 获取当前模式的导航配置
 */
export function getNavigationConfig(mode: "single" | "supervisor"): {
  mainNav: NavItem[];
  systemNav: NavItem[];
  footerNav: NavItem[];
  getAgentConsoleNav: (agentId: string, agentType: string) => NavItem[];
} {
  if (mode === "supervisor") {
    return {
      mainNav: multiModeMainNav,
      systemNav: systemNavItems,
      footerNav: multiModeFooterNav,
      getAgentConsoleNav: getMultiAgentConsoleNav,
    };
  }

  return {
    mainNav: singleModeMainNav,
    systemNav: systemNavItems,
    footerNav: singleModeFooterNav,
    getAgentConsoleNav: getSingleAgentConsoleNav,
  };
}
