"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Bot, Network, Plus, Settings, ArrowRight, Wrench, MessageCircle, Database, Sparkles, Layers, PlayCircle, HelpCircle, Package, FileText, Route } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useModeStore, useAgentStore } from "@/stores";
import { PageHeader } from "@/components/admin";
import { cn } from "@/lib/utils";

export default function WorkspacePage() {
  const router = useRouter();
  const { mode, fetchModeState } = useModeStore();
  const { agents, activeAgent, fetchAgents, isLoading } = useAgentStore();

  useEffect(() => {
    fetchModeState();
    fetchAgents();
  }, [fetchModeState, fetchAgents]);

  const currentAgent = activeAgent();

  // 获取 Agent 类型对应的快捷菜单
  const getAgentQuickLinks = (agentId: string, agentType: string) => {
    const links = [
      { label: "基础设置", href: `/admin/agents/${agentId}`, icon: Settings, description: "名称、描述、系统提示词" },
      { label: "工具配置", href: `/admin/agents/${agentId}/tools`, icon: Wrench, description: "启用/禁用 Agent 工具" },
      { label: "欢迎语", href: `/admin/agents/${agentId}/greeting`, icon: MessageCircle, description: "配置开场白" },
      { label: "推荐问题", href: `/admin/agents/${agentId}/suggested-questions`, icon: HelpCircle, description: "引导用户提问" },
    ];

    if (agentType === "product") {
      links.push({ label: "商品数据", href: "/admin/products", icon: Package, description: "管理商品信息" });
    }
    if (agentType === "faq" || agentType === "kb") {
      links.push({ label: "知识库", href: `/admin/agents/${agentId}/knowledge`, icon: Database, description: "管理知识文档" });
    }
    if (agentType === "faq") {
      links.push({ label: "FAQ 管理", href: `/admin/agents/${agentId}/faq`, icon: HelpCircle, description: "管理常见问题" });
    }

    links.push(
      { label: "技能", href: "/admin/skills", icon: Sparkles, description: "管理 Agent 技能" },
      { label: "中间件", href: `/admin/agents/${agentId}/middleware`, icon: Layers, description: "配置中间件" },
    );

    return links;
  };

  // Supervisor 模式视图
  if (mode === "supervisor") {
    const enabledAgents = agents.filter(a => a.status === "enabled");
    
    return (
      <div className="space-y-6">
        <PageHeader
          title="Supervisor 编排"
          description="管理多个 Agent 的协作与智能路由"
        />

        {/* 编排可视化 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5 text-violet-500" />
              编排架构
            </CardTitle>
            <CardDescription>
              Supervisor 负责接收用户请求，根据路由策略分发给合适的子 Agent
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center gap-6 py-8">
              {/* Supervisor 节点 */}
              <div className="flex flex-col items-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-violet-100 dark:bg-violet-900/30">
                  <Network className="h-8 w-8 text-violet-600 dark:text-violet-400" />
                </div>
                <span className="mt-2 font-medium">Supervisor</span>
                <span className="text-xs text-zinc-500">智能路由</span>
              </div>

              {/* 连接线 */}
              <div className="h-8 w-px bg-zinc-200 dark:bg-zinc-700" />

              {/* 子 Agent 节点 */}
              <div className="flex flex-wrap justify-center gap-4">
                {enabledAgents.map((agent) => (
                  <Link key={agent.id} href={`/admin/agents/${agent.id}`}>
                    <Card className="w-40 cursor-pointer transition-shadow hover:shadow-md">
                      <CardContent className="flex flex-col items-center p-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                          <Bot className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <span className="mt-2 text-sm font-medium truncate w-full text-center">
                          {agent.name}
                        </span>
                        <Badge variant="secondary" className="mt-1 text-xs">
                          {agent.type}
                        </Badge>
                      </CardContent>
                    </Card>
                  </Link>
                ))}

                {/* 添加子 Agent */}
                <Link href="/admin/agents">
                  <Card className="w-40 cursor-pointer border-dashed transition-shadow hover:shadow-md">
                    <CardContent className="flex flex-col items-center justify-center p-4 h-full min-h-[120px]">
                      <Plus className="h-8 w-8 text-zinc-400" />
                      <span className="mt-2 text-sm text-zinc-500">添加子 Agent</span>
                    </CardContent>
                  </Card>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Supervisor 配置入口 */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Link href="/admin/settings/supervisor">
            <Card className="cursor-pointer transition-shadow hover:shadow-md h-full">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100 dark:bg-violet-900/30">
                  <Route className="h-5 w-5 text-violet-600 dark:text-violet-400" />
                </div>
                <div className="flex-1">
                  <div className="font-medium">路由策略</div>
                  <div className="text-sm text-zinc-500">配置请求分发规则</div>
                </div>
                <ArrowRight className="h-4 w-4 text-zinc-400" />
              </CardContent>
            </Card>
          </Link>

          <Link href="/admin/prompts">
            <Card className="cursor-pointer transition-shadow hover:shadow-md h-full">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-900/30">
                  <FileText className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="flex-1">
                  <div className="font-medium">提示词管理</div>
                  <div className="text-sm text-zinc-500">定义 Supervisor 调度行为</div>
                </div>
                <ArrowRight className="h-4 w-4 text-zinc-400" />
              </CardContent>
            </Card>
          </Link>

          <Link href="/">
            <Card className="cursor-pointer transition-shadow hover:shadow-md h-full">
              <CardContent className="flex items-center gap-4 p-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                  <PlayCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div className="flex-1">
                  <div className="font-medium">测试对话</div>
                  <div className="text-sm text-zinc-500">验证路由效果</div>
                </div>
                <ArrowRight className="h-4 w-4 text-zinc-400" />
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* 子 Agent 列表 */}
        <Card>
          <CardHeader>
            <CardTitle>子 Agent 列表</CardTitle>
            <CardDescription>点击编辑子 Agent 的详细配置</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {enabledAgents.length === 0 ? (
                <div className="text-center py-8 text-zinc-500">
                  <Bot className="h-12 w-12 mx-auto mb-4 text-zinc-300" />
                  <p>暂无启用的子 Agent</p>
                  <Button className="mt-4" onClick={() => router.push("/admin/agents")}>
                    添加 Agent
                  </Button>
                </div>
              ) : (
                enabledAgents.map((agent) => (
                  <Link key={agent.id} href={`/admin/agents/${agent.id}`}>
                    <div className="flex items-center justify-between p-4 rounded-lg border hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                          <Bot className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                        </div>
                        <div>
                          <div className="font-medium">{agent.name}</div>
                          <div className="text-sm text-zinc-500">
                            {agent.description || `${agent.type} 类型 Agent`}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant="secondary">{agent.type}</Badge>
                        {agent.is_default && (
                          <Badge variant="outline" className="text-violet-600 border-violet-300">
                            默认
                          </Badge>
                        )}
                        <ArrowRight className="h-4 w-4 text-zinc-400" />
                      </div>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // 单 Agent 模式视图
  const quickLinks = currentAgent ? getAgentQuickLinks(currentAgent.id, currentAgent.type) : [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="工作空间"
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
                  onClick={() => router.push("/admin/agents")}
                >
                  切换 Agent
                </Button>
                <Button
                  onClick={() => router.push(`/admin/agents/${currentAgent.id}`)}
                >
                  编辑配置
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 快捷入口 - 使用现有路由 */}
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

            {/* 测试对话 - 跳转到首页聊天 */}
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
              onClick={() => router.push("/admin/agents")}
            >
              选择 Agent
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 升级提示 */}
      <Card className="border-violet-200 bg-violet-50 dark:border-violet-800 dark:bg-violet-900/20">
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <Network className="h-5 w-5 text-violet-600 dark:text-violet-400" />
            <div>
              <div className="font-medium text-violet-900 dark:text-violet-100">
                需要多 Agent 协作？
              </div>
              <div className="text-sm text-violet-600 dark:text-violet-400">
                切换到 Supervisor 模式，让多个 Agent 协同处理复杂场景
              </div>
            </div>
          </div>
          <Button
            variant="outline"
            className="border-violet-300 text-violet-700 hover:bg-violet-100 dark:border-violet-700 dark:text-violet-300 dark:hover:bg-violet-900/30"
            onClick={() => router.push("/admin/settings/mode")}
          >
            了解更多
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
