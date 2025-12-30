"use client";

import Link from "next/link";
import { Globe, ListTodo, FileText } from "lucide-react";
import { PageHeader } from "@/components/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const crawlerModules = [
  {
    title: "站点配置",
    description: "管理爬取站点配置，包括起始 URL、爬取规则等",
    href: "/admin/crawler/sites",
    icon: Globe,
  },
  {
    title: "任务列表",
    description: "查看爬取任务执行历史和统计信息",
    href: "/admin/crawler/tasks",
    icon: ListTodo,
  },
  {
    title: "页面数据",
    description: "浏览爬取的原始页面数据和解析状态",
    href: "/admin/crawler/pages",
    icon: FileText,
  },
];

export default function CrawlerPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="爬虫管理"
        description="管理站点配置、查看任务和页面数据"
      />

      <div className="grid gap-4 md:grid-cols-3">
        {crawlerModules.map((module) => (
          <Link key={module.href} href={module.href}>
            <Card className="h-full transition-all hover:border-zinc-400 hover:shadow-md dark:hover:border-zinc-600">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-800">
                    <module.icon className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                  </div>
                  <CardTitle className="text-lg">{module.title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  {module.description}
                </p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
