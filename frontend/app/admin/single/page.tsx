"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bot, Settings, Wrench, MessageCircle, HelpCircle, Package, Database, Sparkles, Layers, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAgentStore } from "@/stores";
import { PageHeader } from "@/components/admin";
import { agentHasProductCatalogNav } from "@/lib/config/navigation";

export default function SingleAgentWorkspacePage() {
  const router = useRouter();
  const { agents, activeAgent, fetchAgents, isLoading } = useAgentStore();

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const currentAgent = activeAgent();

  // 获取 Agent 类型对应的快捷菜单
  const getAgentQuickLinks = (agentId: string, agentType: string) => {
    const links = [
      { label: "基础设置", href: `/admin/single/agents/${agentId}`, icon: Settings, description: "名称、描述、系统提示词" },
      { label: "工具配置", href: `/admin/single/agents/${agentId}/tools`, icon: Wrench, description: "启用/禁用 Agent 工具" },
      { label: "欢迎语", href: `/admin/single/agents/${agentId}/greeting`, icon: MessageCircle, description: "配置开场白" },
      { label: "推荐问题", href: `/admin/single/agents/${agentId}/suggested-questions`, icon: HelpCircle, description: "引导用户提问" },
    ];

    if (agentHasProductCatalogNav(agentType)) {
      links.push({ label: "商品数据", href: "/admin/products", icon: Package, description: "管理商品信息" });
    }
    if (agentType === "faq" || agentType === "kb") {
      links.push({ label: "知识库", href: `/admin/single/agents/${agentId}/knowledge`, icon: Database, description: "管理知识文档" });
    }
    if (agentType === "faq") {
      links.push({ label: "FAQ 管理", href: `/admin/single/agents/${agentId}/faq`, icon: HelpCircle, description: "管理常见问题" });
    }

    links.push(
      { label: "技能", href: "/admin/skills", icon: Sparkles, description: "管理 Agent 技能" },
      { label: "中间件", href: `/admin/single/agents/${agentId}/middleware`, icon: Layers, description: "配置中间件" },
    );

    return links;
  };

  const quickLinks = currentAgent ? getAgentQuickLinks(currentAgent.id, currentAgent.type) : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agent 配置"
        description="配置和管理当前激活的 Agent"
      />

      {currentAgent ? (
        <>
          {/* 当前 Agent 信息 */}
          <Card>
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                  <Bot className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{currentAgent.name}</h3>
                  <div className="flex items-center gap-2 text-sm text-zinc-500">
                    <Badge variant="secondary">{currentAgent.type}</Badge>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" />
                      运行中
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => router.push("/admin/single/agents")}
                >
                  切换 Agent
                </Button>
                <Button
                  onClick={() => router.push(`/admin/single/agents/${currentAgent.id}`)}
                >
                  编辑配置
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 快捷入口 */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {quickLinks.map((link) => (
              <Link key={link.href} href={link.href}>
                <Card className="cursor-pointer transition-shadow hover:shadow-md h-full">
                  <CardContent className="p-4">
                    <link.icon className="h-8 w-8 text-zinc-400" />
                    <div className="mt-2 font-medium">{link.label}</div>
                    <div className="text-sm text-zinc-500">{link.description}</div>
                  </CardContent>
                </Card>
              </Link>
            ))}

            {/* 测试对话 */}
            <Link href="/">
              <Card className="cursor-pointer transition-shadow hover:shadow-md h-full">
                <CardContent className="p-4">
                  <PlayCircle className="h-8 w-8 text-emerald-500" />
                  <div className="mt-2 font-medium">测试对话</div>
                  <div className="text-sm text-zinc-500">验证 Agent 效果</div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </>
      ) : (
        /* 未选择 Agent */
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Bot className="h-12 w-12 text-zinc-300" />
            <h3 className="mt-4 text-lg font-medium">未选择 Agent</h3>
            <p className="mt-1 text-sm text-zinc-500">
              请先选择一个 Agent 开始配置
            </p>
            <Button
              className="mt-4"
              onClick={() => router.push("/admin/single/agents")}
            >
              选择 Agent
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
