"use client";

import { useState } from "react";
import { Brain, Check, ChevronDown, ChevronRight, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  LLMCallClusterItem,
  LLMCallSubItem,
  ItemStatus,
} from "@/hooks/use-timeline-reducer";
import { TimelineReasoningItem } from "./TimelineReasoningItem";
import { TimelineContentItem } from "./TimelineContentItem";
import { TimelineProductsItem } from "./TimelineProductsItem";
import { TimelineTodosItem } from "./TimelineTodosItem";
import { TimelineContextSummarizedItem } from "./TimelineContextSummarizedItem";

interface LLMCallClusterProps {
  item: LLMCallClusterItem;
  isStreaming?: boolean;
}

const STATUS_CONFIG: Record<
  ItemStatus,
  { icon: React.ReactNode; text: string; className: string }
> = {
  running: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    text: "思考中…",
    className: "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800",
  },
  success: {
    icon: <Check className="h-4 w-4" />,
    text: "完成",
    className: "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
  },
  error: {
    icon: <XCircle className="h-4 w-4" />,
    text: "失败",
    className: "bg-red-50 text-red-600 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
  },
  empty: {
    icon: <Check className="h-4 w-4" />,
    text: "无结果",
    className: "bg-zinc-50 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
  },
};

function renderSubItem(subItem: LLMCallSubItem, isStreaming: boolean) {
  switch (subItem.type) {
    case "reasoning":
      return (
        <TimelineReasoningItem
          key={subItem.id}
          item={{
            type: "assistant.reasoning",
            id: subItem.id,
            turnId: "",
            text: subItem.text,
            isOpen: subItem.isOpen,
            ts: subItem.ts,
          }}
          isStreaming={isStreaming}
        />
      );
    case "content":
      return (
        <TimelineContentItem
          key={subItem.id}
          item={{
            type: "assistant.content",
            id: subItem.id,
            turnId: "",
            text: subItem.text,
            ts: subItem.ts,
          }}
        />
      );
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

export function LLMCallCluster({ item, isStreaming = false }: LLMCallClusterProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const config = STATUS_CONFIG[item.status];
  const showElapsed = item.status !== "running" && item.elapsedMs !== undefined;
  const hasChildren = item.children.length > 0;

  // 统计子事件
  const hasContent = item.children.some((c) => c.type === "content");
  const hasReasoning = item.children.some((c) => c.type === "reasoning");
  const hasProducts = item.children.some((c) => c.type === "products");

  // 生成摘要
  const getSummary = () => {
    const parts: string[] = [];
    if (hasReasoning) parts.push("推理");
    if (hasContent) parts.push("回复");
    if (hasProducts) parts.push("商品");
    return parts.length > 0 ? parts.join(" · ") : "";
  };

  return (
    <div className="rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden">
      {/* Header - 可点击展开/收起 */}
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2 text-sm cursor-pointer transition-all",
          config.className
        )}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Brain className="h-4 w-4 opacity-60" />
        {config.icon}
        <span className="font-medium">{config.text}</span>
        {showElapsed && (
          <span className="text-xs opacity-70">· {item.elapsedMs}ms</span>
        )}
        {item.error && (
          <span className="text-xs opacity-70">· {item.error}</span>
        )}
        <span className="text-xs opacity-50 ml-auto">{getSummary()}</span>
        {hasChildren && (
          isExpanded ? (
            <ChevronDown className="h-4 w-4 opacity-50" />
          ) : (
            <ChevronRight className="h-4 w-4 opacity-50" />
          )
        )}
      </div>

      {/* Body - 子事件列表 */}
      {isExpanded && hasChildren && (
        <div className="border-t border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900">
          <div className="p-3 space-y-3">
            {item.children.map((child) => renderSubItem(child, isStreaming))}
          </div>
        </div>
      )}
    </div>
  );
}
