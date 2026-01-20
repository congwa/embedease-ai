"use client";

import { useParams, usePathname } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Bot, RefreshCw, Zap, MessageSquareText } from "lucide-react";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import { useAgentStore } from "@/stores";
import { LoadingState, ErrorAlert, StatusBadge } from "@/components/admin";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { useState } from "react";

const typeLabels: Record<string, string> = {
  product: "商品推荐",
  faq: "FAQ 问答",
  kb: "知识库",
  custom: "自定义",
};

// 基础 Tab（所有 Agent 都有）
const baseTabs = [
  { id: "overview", label: "基础设置", href: "" },
  { id: "greeting", label: "开场白", href: "/greeting" },
  { id: "suggested-questions", label: "推荐问题", href: "/suggested-questions" },
  { id: "tools", label: "工具配置", href: "/tools" },
  { id: "middleware", label: "中间件", href: "/middleware" },
  { id: "memory", label: "记忆与提示词", href: "/memory" },
  { id: "conversations", label: "会话洞察", href: "/conversations" },
];

// 根据 Agent 类型获取额外的 Tab
const getTypeTabs = (agentType: string) => {
  const tabs: { id: string; label: string; href: string }[] = [];
  
  if (agentType === "faq") {
    tabs.push({ id: "faq", label: "FAQ 管理", href: "/faq" });
  }
  
  if (agentType === "kb" || agentType === "faq") {
    tabs.push({ id: "knowledge", label: "知识库", href: "/knowledge" });
  }
  
  return tabs;
};

export default function AgentDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const agentId = params.agentId as string;
  const [isActivating, setIsActivating] = useState(false);

  const { agent, isLoading, error, refresh } = useAgentDetail({ agentId });
  const activateAgent = useAgentStore((s) => s.activateAgent);
  const activeAgent = useAgentStore((s) => s.activeAgent());

  // 根据 Agent 类型动态生成 Tab
  const agentTabs = agent
    ? [...baseTabs, ...getTypeTabs(agent.type)]
    : baseTabs;

  const currentTab = agentTabs.find((tab) => {
    const tabPath = `/admin/agents/${agentId}${tab.href}`;
    return pathname === tabPath;
  })?.id || "overview";

  const isCurrentAgentActive = activeAgent?.id === agentId;

  const handleActivate = async () => {
    setIsActivating(true);
    await activateAgent(agentId);
    setIsActivating(false);
    refresh();
  };

  if (isLoading) {
    return <LoadingState text="加载 Agent 详情..." />;
  }

  if (error || !agent) {
    return (
      <div className="space-y-6">
        <Link
          href="/admin/agents"
          className="inline-flex items-center text-sm text-zinc-500 hover:text-zinc-900"
        >
          <ChevronLeft className="mr-1 h-4 w-4" />
          返回列表
        </Link>
        <ErrorAlert error={error || "Agent 不存在"} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 面包屑和返回 */}
      <Link
        href="/admin/agents"
        className="inline-flex items-center text-sm text-zinc-500 hover:text-zinc-900"
      >
        <ChevronLeft className="mr-1 h-4 w-4" />
        返回 Agent 列表
      </Link>

      {/* Agent 头部信息 */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-100 dark:bg-zinc-800">
            <Bot className="h-6 w-6 text-zinc-600 dark:text-zinc-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                {agent.name}
              </h1>
              {isCurrentAgentActive && (
                <Badge className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                  <Zap className="mr-1 h-3 w-3" />
                  当前激活
                </Badge>
              )}
              {agent.is_default && !isCurrentAgentActive && (
                <Badge variant="secondary">默认</Badge>
              )}
              <StatusBadge enabled={agent.status === "enabled"} />
            </div>
            <div className="mt-1 flex items-center gap-2 text-sm text-zinc-500">
              <Badge variant="outline">{typeLabels[agent.type] || agent.type}</Badge>
              <span>·</span>
              <span>模式: {agent.mode_default}</span>
              {agent.knowledge_config?.name && (
                <>
                  <span>·</span>
                  <span>知识库: {agent.knowledge_config.name}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isCurrentAgentActive && agent.status === "enabled" && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="default" size="sm" className="bg-blue-600 hover:bg-blue-700">
                  <Zap className="mr-2 h-4 w-4" />
                  设为激活
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>激活此 Agent</AlertDialogTitle>
                  <AlertDialogDescription className="space-y-2">
                    <p>确定要将 <strong>{agent.name}</strong> 设为激活状态吗？</p>
                    <p className="text-amber-600 dark:text-amber-400">
                      ⚠️ 激活后，所有用户对话将由该 Agent 处理。
                    </p>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handleActivate}
                    disabled={isActivating}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isActivating ? "激活中..." : "确认激活"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新缓存
          </Button>
        </div>
      </div>

      {/* Tab 导航 */}
      <Tabs value={currentTab}>
        <TabsList>
          {agentTabs.map((tab) => (
            <TabsTrigger key={tab.id} value={tab.id} asChild>
              <Link href={`/admin/agents/${agentId}${tab.href}`}>
                {tab.label}
              </Link>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* 页面内容 */}
      {children}
    </div>
  );
}
