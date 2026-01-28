"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Bot, Network, ChevronDown, Check, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useModeStore } from "@/stores";
import { cn } from "@/lib/utils";

interface ModeIndicatorProps {
  className?: string;
  showLabel?: boolean;
}

export function ModeIndicator({ className, showLabel = true }: ModeIndicatorProps) {
  const router = useRouter();
  const { mode, isLoading, switchMode, fetchModeState } = useModeStore();

  useEffect(() => {
    fetchModeState();
  }, [fetchModeState]);

  const handleSwitchMode = async (targetMode: "single" | "supervisor") => {
    if (targetMode === mode) return;
    
    const success = await switchMode(targetMode);
    if (success) {
      router.push("/admin/workspace");
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "gap-2 border-zinc-200 bg-white hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:bg-zinc-800",
            className
          )}
          disabled={isLoading}
        >
          {mode === "supervisor" ? (
            <>
              <Network className="h-4 w-4 text-violet-500" />
              {showLabel && <span>Supervisor</span>}
            </>
          ) : (
            <>
              <Bot className="h-4 w-4 text-emerald-500" />
              {showLabel && <span>单 Agent</span>}
            </>
          )}
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem
          onClick={() => handleSwitchMode("single")}
          className="cursor-pointer"
        >
          <Bot className="mr-2 h-4 w-4 text-emerald-500" />
          <div className="flex flex-1 flex-col">
            <span>单 Agent 模式</span>
            <span className="text-xs text-zinc-500">一个 Agent 处理所有请求</span>
          </div>
          {mode === "single" && <Check className="ml-2 h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => handleSwitchMode("supervisor")}
          className="cursor-pointer"
        >
          <Network className="mr-2 h-4 w-4 text-violet-500" />
          <div className="flex flex-1 flex-col">
            <span>Supervisor 模式</span>
            <span className="text-xs text-zinc-500">多 Agent 协作智能路由</span>
          </div>
          {mode === "supervisor" && <Check className="ml-2 h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => router.push("/admin/settings/mode")}
          className="cursor-pointer"
        >
          <Settings className="mr-2 h-4 w-4" />
          <span>模式设置</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
