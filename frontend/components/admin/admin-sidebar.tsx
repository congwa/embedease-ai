"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Package,
  MessageSquare,
  Users,
  Globe,
  ListTodo,
  FileText,
  Settings,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  {
    title: "仪表盘",
    href: "/admin",
    icon: LayoutDashboard,
  },
  {
    title: "商品管理",
    href: "/admin/products",
    icon: Package,
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
    title: "爬虫管理",
    href: "/admin/crawler",
    icon: Globe,
    children: [
      { title: "站点配置", href: "/admin/crawler/sites" },
      { title: "任务列表", href: "/admin/crawler/tasks" },
      { title: "页面数据", href: "/admin/crawler/pages" },
    ],
  },
];

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-zinc-200 px-4 dark:border-zinc-800">
          <Link href="/admin" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 dark:bg-zinc-100">
              <Settings className="h-4 w-4 text-white dark:text-zinc-900" />
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

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.children &&
                  item.children.some((child) => pathname === child.href));

              return (
                <li key={item.href}>
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
                    {item.title}
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
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t border-zinc-200 p-4 dark:border-zinc-800">
          <Link
            href="/support"
            className="flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
          >
            <MessageSquare className="h-4 w-4" />
            客服工作台
          </Link>
        </div>
      </div>
    </aside>
  );
}
