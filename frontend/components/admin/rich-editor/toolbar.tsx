"use client";

import type { Editor } from "@tiptap/core";
import {
  Bold,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Image,
  Italic,
  Link,
  List,
  ListOrdered,
  ListTodo,
  Quote,
  Redo,
  RemoveFormatting,
  Strikethrough,
  Table,
  Underline,
  Undo,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { FormattingCommand, FormattingState } from "./types";

interface ToolbarProps {
  editor: Editor | null;
  formattingState: FormattingState;
  onCommand: (command: FormattingCommand) => void;
  className?: string;
}

interface ToolbarButtonProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}

function ToolbarButton({ icon, label, active, disabled, onClick }: ToolbarButtonProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClick}
            disabled={disabled}
            className={cn(
              "h-8 w-8 p-0",
              active && "bg-zinc-200 dark:bg-zinc-700"
            )}
          >
            {icon}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          {label}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function ToolbarDivider() {
  return <div className="mx-1 h-5 w-px bg-zinc-200 dark:bg-zinc-700" />;
}

export function Toolbar({ editor, formattingState, onCommand, className }: ToolbarProps) {
  if (!editor) return null;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-0.5 border-b border-zinc-200 bg-zinc-50 px-2 py-1.5 dark:border-zinc-700 dark:bg-zinc-800/50",
        className
      )}
    >
      {/* Text Formatting */}
      <ToolbarButton
        icon={<Bold className="h-4 w-4" />}
        label="粗体"
        active={formattingState.isBold}
        disabled={!formattingState.canBold}
        onClick={() => onCommand("bold")}
      />
      <ToolbarButton
        icon={<Italic className="h-4 w-4" />}
        label="斜体"
        active={formattingState.isItalic}
        disabled={!formattingState.canItalic}
        onClick={() => onCommand("italic")}
      />
      <ToolbarButton
        icon={<Underline className="h-4 w-4" />}
        label="下划线"
        active={formattingState.isUnderline}
        disabled={!formattingState.canUnderline}
        onClick={() => onCommand("underline")}
      />
      <ToolbarButton
        icon={<Strikethrough className="h-4 w-4" />}
        label="删除线"
        active={formattingState.isStrike}
        disabled={!formattingState.canStrike}
        onClick={() => onCommand("strike")}
      />
      <ToolbarButton
        icon={<Code className="h-4 w-4" />}
        label="行内代码"
        active={formattingState.isCode}
        disabled={!formattingState.canCode}
        onClick={() => onCommand("code")}
      />
      <ToolbarButton
        icon={<RemoveFormatting className="h-4 w-4" />}
        label="清除格式"
        disabled={!formattingState.canClearMarks}
        onClick={() => onCommand("clearMarks")}
      />

      <ToolbarDivider />

      {/* Headings */}
      <ToolbarButton
        icon={<Heading1 className="h-4 w-4" />}
        label="标题 1"
        active={formattingState.isHeading1}
        onClick={() => onCommand("heading1")}
      />
      <ToolbarButton
        icon={<Heading2 className="h-4 w-4" />}
        label="标题 2"
        active={formattingState.isHeading2}
        onClick={() => onCommand("heading2")}
      />
      <ToolbarButton
        icon={<Heading3 className="h-4 w-4" />}
        label="标题 3"
        active={formattingState.isHeading3}
        onClick={() => onCommand("heading3")}
      />

      <ToolbarDivider />

      {/* Lists */}
      <ToolbarButton
        icon={<List className="h-4 w-4" />}
        label="无序列表"
        active={formattingState.isBulletList}
        onClick={() => onCommand("bulletList")}
      />
      <ToolbarButton
        icon={<ListOrdered className="h-4 w-4" />}
        label="有序列表"
        active={formattingState.isOrderedList}
        onClick={() => onCommand("orderedList")}
      />
      <ToolbarButton
        icon={<ListTodo className="h-4 w-4" />}
        label="任务列表"
        active={formattingState.isTaskList}
        onClick={() => onCommand("taskList")}
      />

      <ToolbarDivider />

      {/* Blocks */}
      <ToolbarButton
        icon={<Quote className="h-4 w-4" />}
        label="引用"
        active={formattingState.isBlockquote}
        onClick={() => onCommand("blockquote")}
      />
      <ToolbarButton
        icon={<Code className="h-4 w-4" />}
        label="代码块"
        active={formattingState.isCodeBlock}
        onClick={() => onCommand("codeBlock")}
      />
      <ToolbarButton
        icon={<Table className="h-4 w-4" />}
        label="表格"
        active={formattingState.isTable}
        disabled={!formattingState.canTable}
        onClick={() => onCommand("table")}
      />

      <ToolbarDivider />

      {/* Links & Media */}
      <ToolbarButton
        icon={<Link className="h-4 w-4" />}
        label="链接"
        active={formattingState.isLink}
        disabled={!formattingState.canLink}
        onClick={() => onCommand("link")}
      />
      <ToolbarButton
        icon={<Image className="h-4 w-4" />}
        label="图片"
        disabled={!formattingState.canImage}
        onClick={() => onCommand("image")}
      />

      <ToolbarDivider />

      {/* History */}
      <ToolbarButton
        icon={<Undo className="h-4 w-4" />}
        label="撤销"
        disabled={!formattingState.canUndo}
        onClick={() => onCommand("undo")}
      />
      <ToolbarButton
        icon={<Redo className="h-4 w-4" />}
        label="重做"
        disabled={!formattingState.canRedo}
        onClick={() => onCommand("redo")}
      />
    </div>
  );
}
