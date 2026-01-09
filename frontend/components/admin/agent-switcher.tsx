"use client";

/**
 * Agent 切换器组件
 * 
 * 显示当前激活的 Agent，支持快速切换到其他 Agent。
 * 用于侧边栏顶部，让用户始终了解当前工作的 Agent 上下文。
 */

import { useState } from "react";
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
              "w-full justify-between bg-zinc-50 dark:bg-zinc-900",
              className
            )}
            disabled={isLoading}
          >
            <div className="flex items-center gap-2 truncate">
              <div className="flex h-6 w-6 items-center justify-center rounded bg-zinc-200 dark:bg-zinc-700">
                <TypeIcon className="h-3.5 w-3.5" />
              </div>
              <div className="flex flex-col items-start truncate">
                <span className="truncate text-sm font-medium">
                  {activeAgent?.name || "选择 Agent"}
                </span>
                {activeAgent && (
                  <span className="text-xs text-zinc-500">
                    {typeLabels[activeAgent.type]}
                  </span>
                )}
              </div>
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
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
            <AlertDialogDescription className="space-y-2">
              <p>
                确定要将 <strong>{confirmAgent?.name}</strong> 设为激活状态吗？
              </p>
              <p className="text-amber-600 dark:text-amber-400">
                ⚠️ 激活后，所有用户对话将由该 Agent 处理。
              </p>
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
    <CommandItem onSelect={onSelect} className="flex items-center gap-2">
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded",
          isActive
            ? "bg-blue-100 dark:bg-blue-900"
            : "bg-zinc-100 dark:bg-zinc-800"
        )}
      >
        <TypeIcon
          className={cn(
            "h-4 w-4",
            isActive
              ? "text-blue-600 dark:text-blue-400"
              : "text-zinc-600 dark:text-zinc-400"
          )}
        />
      </div>
      <div className="flex-1 truncate">
        <div className="flex items-center gap-2">
          <span className="font-medium">{agent.name}</span>
          {isActive && (
            <Badge
              variant="secondary"
              className="bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
            >
              激活
            </Badge>
          )}
        </div>
        <span className="text-xs text-zinc-500">
          {typeLabels[agent.type]}
        </span>
      </div>
      {isActive && <Check className="h-4 w-4 text-green-600" />}
    </CommandItem>
  );
}
