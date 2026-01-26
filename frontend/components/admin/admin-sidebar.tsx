"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Package,
  MessageSquare,
  Users,
  Globe,
  Settings,
  ChevronLeft,
  HelpCircle,
  Database,
  Bot,
  Wrench,
  BarChart3,
  FileText,
  Zap,
  Sparkles,
  Wand2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { AgentSwitcher } from "./agent-switcher";
import { useAgentStore } from "@/stores";
import { useSupportStats } from "@/hooks/use-support-stats";

// 基础菜单（始终显示）
const baseNavItems = [
  {
    title: "仪表盘",
    href: "/admin",
    icon: LayoutDashboard,
  },
  {
    title: "Quick Setup",
    href: "/admin/quick-setup",
    icon: Sparkles,
  },
];

// Agent 控制台菜单（根据当前激活 Agent 动态生成）
const getAgentConsoleItems = (agentId: string, agentType: string) => {
  const baseItems = [
    {
      title: "基础设置",
      href: `/admin/agents/${agentId}`,
      icon: Settings,
    },
    {
      title: "工具配置",
      href: `/admin/agents/${agentId}/tools`,
      icon: Wrench,
    },
    {
      title: "会话洞察",
      href: `/admin/agents/${agentId}/conversations`,
      icon: BarChart3,
    },
  ];

  // 根据 Agent 类型添加特定菜单
  if (agentType === "product") {
    baseItems.push({
      title: "商品数据",
      href: "/admin/products",
      icon: Package,
    });
  }

  if (agentType === "faq") {
    baseItems.push({
      title: "FAQ 管理",
      href: `/admin/agents/${agentId}/faq`,
      icon: HelpCircle,
    });
  }

  if (agentType === "kb" || agentType === "faq") {
    baseItems.push({
      title: "知识库",
      href: `/admin/agents/${agentId}/knowledge`,
      icon: Database,
    });
  }

  return baseItems;
};

// 系统管理菜单
const systemNavItems = [
  {
    title: "Agent 列表",
    href: "/admin/agents",
    icon: Bot,
  },
  {
    title: "技能管理",
    href: "/admin/skills",
    icon: Wand2,
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
  },
  {
    title: "用户管理",
    href: "/admin/users",
    icon: Users,
  },
  {
    title: "设置中心",
    href: "/admin/settings",
    icon: Settings,
  },
];

function NavItem({
  item,
  pathname,
}: {
  item: { title: string; href: string; icon: React.ElementType; children?: { title: string; href: string }[] };
  pathname: string;
}) {
  const isActive =
    pathname === item.href ||
    pathname.startsWith(item.href + "/") ||
    (item.children && item.children.some((child) => pathname === child.href));

  return (
    <li>
      <Link
        href={item.href}
        className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
          isActive
            ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
            : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
        )}
      >
        <item.icon className="h-4 w-4" />
        <span className="flex-1">{item.title}</span>
      </Link>
      {item.children && isActive && (
        <ul className="ml-7 mt-1 space-y-1">
          {item.children.map((child) => (
            <li key={child.href}>
              <Link
                href={child.href}
                className={cn(
                  "block rounded-lg px-3 py-1.5 text-sm transition-colors",
                  pathname === child.href
                    ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                    : "text-zinc-500 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-500 dark:hover:bg-zinc-900 dark:hover:text-zinc-100"
                )}
              >
                {child.title}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function AdminSidebar() {
  const pathname = usePathname();
  const activeAgent = useAgentStore((s) => s.activeAgent());
  const isLoading = useAgentStore((s) => s.isLoading);
  const { stats: supportStats, hasNotification } = useSupportStats();

  // 根据当前激活 Agent 生成控制台菜单
  const agentConsoleItems = activeAgent
    ? getAgentConsoleItems(activeAgent.id, activeAgent.type)
    : [];

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
          <Link href="/admin" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 dark:bg-zinc-100">
              <Zap className="h-4 w-4 text-white dark:text-zinc-900" />
            </div>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">
              管理后台
            </span>
          </Link>
          <Link href="/">
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* Agent 切换器 */}
        <div className="border-b border-zinc-200 p-3 dark:border-zinc-800">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-zinc-500">当前 Agent</span>
            {activeAgent && (
              <Badge
                variant="secondary"
                className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
              >
                激活中
              </Badge>
            )}
          </div>
          <AgentSwitcher />
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          {/* 基础菜单 */}
          <ul className="space-y-1">
            {baseNavItems.map((item) => (
              <NavItem key={item.href} item={item} pathname={pathname} />
            ))}
          </ul>

          {/* Agent 控制台菜单 */}
          {activeAgent && agentConsoleItems.length > 0 && (
            <>
              <Separator className="my-4" />
              <div className="mb-2 px-3">
                <span className="text-xs font-medium text-zinc-500">
                  {activeAgent.name} 控制台
                </span>
              </div>
              <ul className="space-y-1">
                {agentConsoleItems.map((item) => (
                  <NavItem key={item.href} item={item} pathname={pathname} />
                ))}
              </ul>
            </>
          )}

          {/* 系统管理菜单 */}
          <Separator className="my-4" />
          <div className="mb-2 px-3">
            <span className="text-xs font-medium text-zinc-500">系统管理</span>
          </div>
          <ul className="space-y-1">
            {systemNavItems.map((item) => (
              <NavItem key={item.href} item={item} pathname={pathname} />
            ))}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-200 p-4 dark:border-zinc-800">
          <Link
            href="/support"
            className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
          >
            <div className="flex items-center gap-2">
              <div className="relative">
                <MessageSquare className="h-4 w-4" />
                {/* 红点提醒 */}
                {hasNotification && (
                  <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-red-500" />
                )}
              </div>
              客服工作台
            </div>
            {/* 待处理数量 */}
            {supportStats.pending_count > 0 && (
              <Badge
                variant="secondary"
                className="bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
              >
                {supportStats.pending_count > 99 ? "99+" : supportStats.pending_count}
              </Badge>
            )}
          </Link>
        </div>
      </div>
    </aside>
  );
}
