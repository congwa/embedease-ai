"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
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
  Network,
  Briefcase,
  Route,
  ArrowLeftRight,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AgentSwitcher } from "./agent-switcher";
import { useAgentStore, useModeStore } from "@/stores";
import { useSupportStats } from "@/hooks/use-support-stats";
import { agentHasProductCatalogNav } from "@/lib/config/navigation";

// 单 Agent 模式菜单
const singleModeNavItems: NavItemConfig[] = [
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
    highlight: true,
    highlightColor: "emerald",
  },
];

// Supervisor 模式菜单
const supervisorModeNavItems: NavItemConfig[] = [
  {
    title: "仪表盘",
    href: "/admin",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    title: "Supervisor 编排",
    href: "/admin/supervisor",
    icon: Network,
    highlight: true,
    highlightColor: "violet",
  },
  {
    title: "路由策略",
    href: "/admin/settings/supervisor",
    icon: Route,
  },
];

// Agent 控制台菜单（根据当前激活 Agent 动态生成）
const getAgentConsoleItems = (agentId: string, agentType: string): NavItemConfig[] => {
  const baseItems: NavItemConfig[] = [
    {
      title: "基础设置",
      href: `/admin/agents/${agentId}`,
      icon: Settings,
      exact: true,  // 精确匹配，避免与子路径冲突
    },
    {
      title: "工具配置",
      href: `/admin/agents/${agentId}/tools`,
      icon: Wrench,
      exact: true,
    },
    {
      title: "会话洞察",
      href: `/admin/agents/${agentId}/conversations`,
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
      href: `/admin/agents/${agentId}/faq`,
      icon: HelpCircle,
      exact: true,
    });
  }

  if (agentType === "kb" || agentType === "faq") {
    baseItems.push({
      title: "知识库",
      href: `/admin/agents/${agentId}/knowledge`,
      icon: Database,
      exact: true,
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
    exact: true,  // 精确匹配，避免与 Agent 控制台子路径冲突
  },
  {
    title: "技能管理",
    href: "/admin/skills",
    icon: Wand2,
  },
  {
    title: "提示词管理",
    href: "/admin/prompts",
    icon: FileText,
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

interface NavItemConfig {
  title: string;
  href: string;
  icon: React.ElementType;
  exact?: boolean;
  highlight?: boolean;
  highlightColor?: "emerald" | "violet";
  children?: { title: string; href: string }[];
}

function NavItem({
  item,
  pathname,
}: {
  item: NavItemConfig;
  pathname: string;
}) {
  const isActive = item.exact
    ? pathname === item.href
    : pathname === item.href ||
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
            : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-100",
          item.highlight && !isActive && item.highlightColor === "emerald" && "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-300 dark:hover:bg-emerald-900/30",
          item.highlight && !isActive && item.highlightColor === "violet" && "bg-violet-50 text-violet-700 hover:bg-violet-100 dark:bg-violet-900/20 dark:text-violet-300 dark:hover:bg-violet-900/30"
        )}
      >
        <item.icon className={cn(
          "h-4 w-4",
          item.highlight && item.highlightColor === "emerald" && "text-emerald-500",
          item.highlight && item.highlightColor === "violet" && "text-violet-500"
        )} />
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
  const { mode, switchMode } = useModeStore();
  const { stats: supportStats, hasNotification } = useSupportStats();
  const [showSwitchDialog, setShowSwitchDialog] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);

  // 根据当前模式选择菜单
  const modeNavItems = mode === "supervisor" ? supervisorModeNavItems : singleModeNavItems;

  // 根据当前激活 Agent 生成控制台菜单
  const agentConsoleItems = activeAgent
    ? getAgentConsoleItems(activeAgent.id, activeAgent.type)
    : [];

  const targetMode = mode === "supervisor" ? "single" : "supervisor";
  const targetModeLabel = mode === "supervisor" ? "单 Agent 模式" : "Supervisor 模式";

  const handleSwitchMode = async () => {
    setIsSwitching(true);
    await switchMode(targetMode);
    setIsSwitching(false);
    setShowSwitchDialog(false);
  };

  return (
    <>
      <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex h-16 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
            <Link href="/admin" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 dark:bg-zinc-100">
                <Zap className="h-4 w-4 text-white dark:text-zinc-900" />
              </div>
              <div className="flex flex-col">
                <span className="font-semibold text-zinc-900 dark:text-zinc-100">
                  管理后台
                </span>
                <span className={cn(
                  "text-[10px] font-medium flex items-center gap-1",
                  mode === "supervisor" ? "text-violet-500" : "text-emerald-500"
                )}>
                  {mode === "supervisor" ? (
                    <><Network className="h-3 w-3" /> Supervisor</>
                  ) : (
                    <><Bot className="h-3 w-3" /> 单 Agent</>
                  )}
                </span>
              </div>
            </Link>
            <Link href="/">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </Link>
          </div>

          {/* Agent 切换器 - 仅在单 Agent 模式下显示 */}
          {mode === "single" && (
            <div className="border-b border-zinc-200/50 p-4 dark:border-zinc-800/50">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  当前 Agent
                </span>
                {activeAgent && (
                  <span className="flex items-center gap-1.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                    </span>
                    运行中
                  </span>
                )}
              </div>
              <AgentSwitcher />
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            {/* 模式菜单 */}
            <ul className="space-y-1">
              {modeNavItems.map((item) => (
                <NavItem key={item.href} item={item} pathname={pathname} />
              ))}
            </ul>

            {/* Agent 控制台菜单 - 仅在单 Agent 模式下显示 */}
            {mode === "single" && activeAgent && agentConsoleItems.length > 0 && (
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

          {/* Footer - 模式切换按钮 + 客服工作台 */}
          <div className="border-t border-zinc-200 p-4 space-y-2 dark:border-zinc-800">
            {/* 模式切换按钮 */}
            <Button
              variant="outline"
              size="sm"
              className={cn(
                "w-full justify-start gap-2",
                mode === "supervisor"
                  ? "border-emerald-200 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-800 dark:text-emerald-400 dark:hover:bg-emerald-900/20"
                  : "border-violet-200 text-violet-700 hover:bg-violet-50 dark:border-violet-800 dark:text-violet-400 dark:hover:bg-violet-900/20"
              )}
              onClick={() => setShowSwitchDialog(true)}
            >
              <ArrowLeftRight className="h-4 w-4" />
              切换到{targetModeLabel}
            </Button>

            {/* 客服工作台 */}
            <Link
              href="/support"
              className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
            >
              <div className="flex items-center gap-2">
                <div className="relative">
                  <MessageSquare className="h-4 w-4" />
                  {hasNotification && (
                    <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-red-500" />
                  )}
                </div>
                客服工作台
              </div>
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

      {/* 模式切换确认弹窗 */}
      <AlertDialog open={showSwitchDialog} onOpenChange={setShowSwitchDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              {mode === "supervisor" ? (
                <Bot className="h-5 w-5 text-emerald-500" />
              ) : (
                <Network className="h-5 w-5 text-violet-500" />
              )}
              切换到{targetModeLabel}
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3">
                <p>
                  {mode === "supervisor"
                    ? "切换后，所有用户请求将由当前激活的单个 Agent 处理。"
                    : "切换后，多个 Agent 将协作处理用户请求，由 Supervisor 智能路由。"}
                </p>
                <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-700 dark:bg-amber-900/20 dark:text-amber-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    {mode === "supervisor"
                      ? "Supervisor 编排配置将暂停生效。"
                      : "请确保已配置好 Supervisor 路由策略。"}
                  </span>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSwitching}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleSwitchMode}
              disabled={isSwitching}
              className={cn(
                mode === "supervisor"
                  ? "bg-emerald-600 hover:bg-emerald-700"
                  : "bg-violet-600 hover:bg-violet-700"
              )}
            >
              {isSwitching ? "切换中..." : "确认切换"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
