"use client";

import { memo } from "react";
import Link from "next/link";
import { Edit2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/prompt-kit/markdown";

export interface PromptViewerProps {
  /** Markdown 内容 */
  content: string;
  /** 自定义类名 */
  className?: string;
  /** 最大高度，超出滚动 */
  maxHeight?: string | number;
  /** 是否显示边框 */
  bordered?: boolean;
  /** 是否使用紧凑模式 */
  compact?: boolean;
  /** 编辑链接（提供后悬停显示编辑按钮） */
  editHref?: string;
  /** 编辑按钮点击回调（与 editHref 二选一） */
  onEdit?: () => void;
  /** 编辑按钮文本 */
  editLabel?: string;
}

/**
 * 提示词查看器组件
 * 
 * 统一用于显示提示词内容，支持 Markdown 渲染
 * 可配置编辑入口（悬停显示编辑按钮）
 */
function PromptViewerComponent({
  content,
  className,
  maxHeight = "400px",
  bordered = true,
  compact = false,
  editHref,
  onEdit,
  editLabel = "编辑",
}: PromptViewerProps) {
  const canEdit = editHref || onEdit;

  if (!content) {
    return (
      <div
        className={cn(
          "group relative text-sm text-muted-foreground italic",
          bordered && "rounded-lg border bg-muted/30 p-4",
          className
        )}
      >
        暂无内容
        {canEdit && <EditButton href={editHref} onClick={onEdit} label={editLabel} />}
      </div>
    );
  }

  const maxHeightStyle = typeof maxHeight === "number" ? `${maxHeight}px` : maxHeight;

  return (
    <div
      className={cn(
        "group relative overflow-auto",
        bordered && "rounded-lg border bg-muted/30",
        compact ? "p-3" : "p-4",
        className
      )}
      style={{ maxHeight: maxHeightStyle }}
    >
      {canEdit && <EditButton href={editHref} onClick={onEdit} label={editLabel} />}
      <Markdown
        className={cn(
          "prose prose-sm dark:prose-invert max-w-none",
          "prose-headings:font-semibold prose-headings:text-foreground",
          "prose-p:text-foreground prose-p:leading-relaxed",
          "prose-li:text-foreground",
          "prose-code:text-sm prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded",
          "prose-pre:bg-muted prose-pre:border prose-pre:border-border",
          compact && "prose-p:my-1 prose-headings:my-2"
        )}
      >
        {content}
      </Markdown>
    </div>
  );
}

/** 编辑按钮组件 */
function EditButton({
  href,
  onClick,
  label,
}: {
  href?: string;
  onClick?: () => void;
  label: string;
}) {
  const buttonContent = (
    <Button
      variant="secondary"
      size="sm"
      className="h-8 gap-1.5 opacity-0 transition-opacity group-hover:opacity-100"
      onClick={onClick}
    >
      <Edit2 className="h-3.5 w-3.5" />
      {label}
    </Button>
  );

  return (
    <div className="absolute right-2 top-2 z-10">
      {href ? (
        <Link href={href}>{buttonContent}</Link>
      ) : (
        buttonContent
      )}
    </div>
  );
}

export const PromptViewer = memo(PromptViewerComponent);
PromptViewer.displayName = "PromptViewer";
