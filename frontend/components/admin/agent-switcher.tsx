"use client";

/**
 * Agent 切换器组件
 * 
 * 显示当前激活的 Agent，支持快速切换到其他 Agent。
 * 用于侧边栏顶部，让用户始终了解当前工作的 Agent 上下文。
 */

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  Check,
  ChevronsUpDown,
  Package,
  HelpCircle,
  Database,
  Sparkles,
  Zap,
  Network,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
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
import { useAgentStore, type Agent } from "@/stores";

const typeIcons: Record<string, React.ElementType> = {
  product: Package,
  faq: HelpCircle,
  kb: Database,
  custom: Sparkles,
};

const typeColors: Record<string, string> = {
  product: "from-orange-500 to-amber-500",
  faq: "from-blue-500 to-cyan-500",
  kb: "from-violet-500 to-purple-500",
  custom: "from-pink-500 to-rose-500",
};

const typeColorsBg: Record<string, string> = {
  product: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
  faq: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  kb: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  custom: "bg-pink-500/10 text-pink-600 dark:text-pink-400",
};

const typeLabels: Record<string, string> = {
  product: "商品推荐",
  faq: "FAQ 问答",
  kb: "知识库",
  custom: "自定义",
};

interface AgentSwitcherProps {
  className?: string;
  collapsed?: boolean;
}

export function AgentSwitcher({ className, collapsed }: AgentSwitcherProps) {
  const router = useRouter();
  const activeAgent = useAgentStore((s) => s.activeAgent());
  const agents = useAgentStore((s) => s.agents);
  const activateAgent = useAgentStore((s) => s.activateAgent);
  const isLoading = useAgentStore((s) => s.isLoading);
  const [open, setOpen] = useState(false);
  const [confirmAgent, setConfirmAgent] = useState<Agent | null>(null);
  const [isActivating, setIsActivating] = useState(false);
  const fetchAgents = useAgentStore((s) => s.fetchAgents);
  const hasFetched = useRef(false);

  // 初始化时加载 Agent 列表
  useEffect(() => {
    if (!hasFetched.current) {
      hasFetched.current = true;
      fetchAgents();
    }
  }, [fetchAgents]);

  const handleSelect = (agent: Agent) => {
    if (agent.is_default) {
      // 已经是激活的，直接进入控制台
      router.push(`/admin/agents/${agent.id}`);
      setOpen(false);
    } else {
      // 需要确认切换
      setConfirmAgent(agent);
      setOpen(false);
    }
  };

  const handleConfirmActivate = async () => {
    if (!confirmAgent) return;

    setIsActivating(true);
    const success = await activateAgent(confirmAgent.id);
    setIsActivating(false);

    if (success) {
      router.push(`/admin/agents/${confirmAgent.id}`);
    }
    setConfirmAgent(null);
  };

  const TypeIcon = activeAgent ? typeIcons[activeAgent.type] || Bot : Bot;

  if (collapsed) {
    return (
      <Button
        variant="ghost"
        size="icon"
        className={cn("h-10 w-10", className)}
        onClick={() => setOpen(true)}
      >
        <TypeIcon className="h-5 w-5" />
      </Button>
    );
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className={cn(
              "group h-auto w-full justify-between border-zinc-200/80 bg-gradient-to-b from-white to-zinc-50/50 px-4 py-3 shadow-sm transition-all hover:border-zinc-300 hover:shadow-md dark:border-zinc-700/80 dark:from-zinc-800 dark:to-zinc-900/50 dark:hover:border-zinc-600",
              className
            )}
            disabled={isLoading}
          >
            <div className="flex items-center gap-3.5 truncate">
              <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br shadow-sm",
                activeAgent ? typeColors[activeAgent.type] : "from-zinc-400 to-zinc-500"
              )}>
                <TypeIcon className="h-5 w-5 text-white drop-shadow-sm" />
              </div>
              <div className="flex flex-col items-start gap-0.5 truncate">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                    {activeAgent?.name || "选择 Agent"}
                  </span>
                  {activeAgent?.is_supervisor && (
                    <span className="inline-flex items-center gap-0.5 rounded bg-orange-500/10 px-1 py-0.5 text-[9px] font-semibold text-orange-600 dark:text-orange-400">
                      <Network className="h-2.5 w-2.5" />
                      Supervisor
                    </span>
                  )}
                </div>
                {activeAgent && (
                  <span className={cn(
                    "text-xs font-medium",
                    typeColorsBg[activeAgent.type]?.split(" ").slice(1).join(" ") || "text-zinc-500"
                  )}>
                    {typeLabels[activeAgent.type]}
                  </span>
                )}
              </div>
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 text-zinc-400 transition-transform group-hover:text-zinc-600 dark:text-zinc-500 dark:group-hover:text-zinc-300" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[280px] p-0" align="start">
          <Command>
            <CommandInput placeholder="搜索 Agent..." />
            <CommandList>
              <CommandEmpty>没有找到 Agent</CommandEmpty>
              <CommandGroup heading="当前激活">
                {activeAgent && (
                  <AgentCommandItem
                    agent={activeAgent}
                    isActive
                    onSelect={() => handleSelect(activeAgent)}
                  />
                )}
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup heading="其他 Agent">
                {agents
                  .filter((a) => !a.is_default && a.status === "enabled")
                  .map((agent) => (
                    <AgentCommandItem
                      key={agent.id}
                      agent={agent}
                      onSelect={() => handleSelect(agent)}
                    />
                  ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      {/* 激活确认对话框 */}
      <AlertDialog
        open={!!confirmAgent}
        onOpenChange={() => setConfirmAgent(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>切换激活 Agent</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  确定要将 <strong>{confirmAgent?.name}</strong> 设为激活状态吗？
                </p>
                <p className="text-amber-600 dark:text-amber-400">
                  ⚠️ 激活后，所有用户对话将由该 Agent 处理。
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isActivating}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmActivate}
              disabled={isActivating}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isActivating ? (
                <>
                  <Zap className="mr-2 h-4 w-4 animate-pulse" />
                  激活中...
                </>
              ) : (
                <>
                  <Zap className="mr-2 h-4 w-4" />
                  确认激活
                </>
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function AgentCommandItem({
  agent,
  isActive,
  onSelect,
}: {
  agent: Agent;
  isActive?: boolean;
  onSelect: () => void;
}) {
  const TypeIcon = typeIcons[agent.type] || Bot;

  return (
    <CommandItem 
      onSelect={onSelect} 
      className="flex items-center gap-3 px-3 py-2.5"
    >
      <div
        className={cn(
          "flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br shadow-sm",
          isActive
            ? typeColors[agent.type]
            : "from-zinc-200 to-zinc-300 dark:from-zinc-700 dark:to-zinc-800"
        )}
      >
        <TypeIcon
          className={cn(
            "h-4 w-4",
            isActive
              ? "text-white drop-shadow-sm"
              : "text-zinc-600 dark:text-zinc-400"
          )}
        />
      </div>
      <div className="flex-1 truncate">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-zinc-800 dark:text-zinc-100">
            {agent.name}
          </span>
          {isActive && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              当前
            </span>
          )}
        </div>
        <span className={cn(
          "text-[11px] font-medium",
          typeColorsBg[agent.type]?.split(" ").slice(1).join(" ") || "text-zinc-500"
        )}>
          {typeLabels[agent.type]}
        </span>
      </div>
      {isActive && <Check className="h-4 w-4 text-emerald-500" />}
    </CommandItem>
  );
}
