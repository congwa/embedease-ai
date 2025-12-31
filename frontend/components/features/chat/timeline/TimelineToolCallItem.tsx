"use client";

import { useState } from "react";
import { Loader2, Check, XCircle, Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolCallItem, ItemStatus, ToolCallSubItem } from "@/hooks/use-timeline-reducer";
import { TimelineProductsItem } from "./TimelineProductsItem";
import { TimelineTodosItem } from "./TimelineTodosItem";
import { TimelineContextSummarizedItem } from "./TimelineContextSummarizedItem";

interface TimelineToolCallItemProps {
  item: ToolCallItem;
}

const STATUS_CONFIG: Record<
  ItemStatus,
  { icon: React.ReactNode; className: string }
> = {
  running: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    className: "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
  },
  success: {
    icon: <Check className="h-4 w-4" />,
    className: "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
  },
  error: {
    icon: <XCircle className="h-4 w-4" />,
    className: "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
  },
  empty: {
    icon: <Check className="h-4 w-4 opacity-60" />,
    className: "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
  },
};

function getStatusText(item: ToolCallItem): string {
  switch (item.status) {
    case "running":
      return `${item.label}中…`;
    case "success":
      return `${item.label}完成`;
    case "error":
      return `${item.label}失败`;
    case "empty":
      return `${item.label}无结果`;
    default:
      return item.label;
  }
}

function renderSubItem(subItem: ToolCallSubItem) {
  switch (subItem.type) {
    case "products":
      return (
        <TimelineProductsItem
          key={subItem.id}
          item={{
            type: "assistant.products",
            id: subItem.id,
            turnId: "",
            products: subItem.products,
            ts: subItem.ts,
          }}
        />
      );
    case "todos":
      return (
        <TimelineTodosItem
          key={subItem.id}
          item={{
            type: "assistant.todos",
            id: subItem.id,
            turnId: "",
            todos: subItem.todos,
            ts: subItem.ts,
          }}
        />
      );
    case "context_summarized":
      return (
        <TimelineContextSummarizedItem
          key={subItem.id}
          item={{
            type: "context.summarized",
            id: subItem.id,
            turnId: "",
            messagesBefore: subItem.messagesBefore,
            messagesAfter: subItem.messagesAfter,
            tokensBefore: subItem.tokensBefore,
            tokensAfter: subItem.tokensAfter,
            ts: subItem.ts,
          }}
        />
      );
    default:
      return null;
  }
}

export function TimelineToolCallItem({ item }: TimelineToolCallItemProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const config = STATUS_CONFIG[item.status];
  const showStats = item.status !== "running";
  const hasChildren = item.children && item.children.length > 0;

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden">
      {/* Header */}
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2 text-sm transition-all",
          hasChildren && "cursor-pointer",
          config.className
        )}
        onClick={() => hasChildren && setIsExpanded(!isExpanded)}
      >
        <Wrench className="h-4 w-4 opacity-60" />
        {config.icon}
        <span className="font-medium">{getStatusText(item)}</span>
        {showStats && item.count !== undefined && (
          <span className="text-xs opacity-70">· {item.count}项</span>
        )}
        {showStats && item.elapsedMs !== undefined && (
          <span className="text-xs opacity-70">· {item.elapsedMs}ms</span>
        )}
        {item.error && (
          <span className="text-xs opacity-70 ml-auto">{item.error}</span>
        )}
        {hasChildren && (
          <span className="ml-auto">
            {isExpanded ? (
              <ChevronDown className="h-4 w-4 opacity-50" />
            ) : (
              <ChevronRight className="h-4 w-4 opacity-50" />
            )}
          </span>
        )}
      </div>

      {/* Children - 工具执行期间的数据事件 */}
      {isExpanded && hasChildren && (
        <div className="border-t border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
          <div className="p-3 space-y-3">
            {item.children.map((child) => renderSubItem(child))}
          </div>
        </div>
      )}
    </div>
  );
}
