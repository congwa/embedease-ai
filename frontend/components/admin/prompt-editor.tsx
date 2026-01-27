"use client";

import { memo, useEffect, useCallback } from "react";
import { EditorContent } from "@tiptap/react";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Code,
  Heading1,
  Heading2,
  Heading3,
  Quote,
  Undo,
  Redo,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useRichEditor } from "@/components/rich-editor/use-rich-editor";
import { markdownToHtml } from "@/components/rich-editor/helpers/markdown-converter";
import "@/components/rich-editor/editor-styles.css";

export interface PromptEditorProps {
  /** 初始 Markdown 内容 */
  value: string;
  /** 内容变更回调 */
  onChange: (markdown: string) => void;
  /** 自定义类名 */
  className?: string;
  /** 编辑器最小高度 */
  minHeight?: string | number;
  /** 编辑器最大高度 */
  maxHeight?: string | number;
  /** 占位符文本 */
  placeholder?: string;
  /** 是否禁用 */
  disabled?: boolean;
  /** 是否显示工具栏 */
  showToolbar?: boolean;
  /** 是否显示 Markdown 预览 */
  showMarkdownPreview?: boolean;
}

interface ToolbarButtonProps {
  onClick: () => void;
  isActive?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
}

const ToolbarButton = memo(function ToolbarButton({
  onClick,
  isActive,
  disabled,
  title,
  children,
}: ToolbarButtonProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant={isActive ? "secondary" : "ghost"}
          size="icon"
          className="h-8 w-8"
          onClick={onClick}
          disabled={disabled}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="bottom">{title}</TooltipContent>
    </Tooltip>
  );
});

/**
 * 提示词编辑器组件
 * 
 * 统一用于编辑提示词内容，支持富文本编辑和 Markdown 输出
 */
function PromptEditorComponent({
  value,
  onChange,
  className,
  minHeight = 300,
  maxHeight = 500,
  placeholder = "输入提示词内容...",
  disabled = false,
  showToolbar = true,
  showMarkdownPreview = false,
}: PromptEditorProps) {
  const { editor, markdown, setMarkdown } = useRichEditor({
    initialContent: value,
    placeholder,
    editable: !disabled,
    onChange: (newMarkdown) => {
      onChange(newMarkdown);
    },
  });

  // 同步外部 value 变化到编辑器
  const syncValue = useCallback(() => {
    if (editor && !editor.isDestroyed && value !== markdown) {
      const html = markdownToHtml(value);
      editor.commands.setContent(html);
    }
  }, [editor, value, markdown]);

  // 仅在 value prop 变化且与当前 markdown 不同时同步
  useEffect(() => {
    // 只在初始化或外部强制更新时同步
    if (editor && value && value !== markdown && !editor.isFocused) {
      syncValue();
    }
  }, [value, editor]);

  const minHeightStyle = typeof minHeight === "number" ? `${minHeight}px` : minHeight;
  const maxHeightStyle = typeof maxHeight === "number" ? `${maxHeight}px` : maxHeight;

  return (
    <div className={cn("space-y-2", className)}>
      {/* 工具栏 */}
      {showToolbar && (
        <TooltipProvider delayDuration={300}>
          <div className="flex flex-wrap items-center gap-1 rounded-lg border bg-muted/30 p-1">
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleBold().run()}
              isActive={editor?.isActive("bold")}
              disabled={disabled}
              title="粗体"
            >
              <Bold className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleItalic().run()}
              isActive={editor?.isActive("italic")}
              disabled={disabled}
              title="斜体"
            >
              <Italic className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleCode().run()}
              isActive={editor?.isActive("code")}
              disabled={disabled}
              title="行内代码"
            >
              <Code className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
              isActive={editor?.isActive("heading", { level: 1 })}
              disabled={disabled}
              title="标题 1"
            >
              <Heading1 className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
              isActive={editor?.isActive("heading", { level: 2 })}
              disabled={disabled}
              title="标题 2"
            >
              <Heading2 className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
              isActive={editor?.isActive("heading", { level: 3 })}
              disabled={disabled}
              title="标题 3"
            >
              <Heading3 className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleBulletList().run()}
              isActive={editor?.isActive("bulletList")}
              disabled={disabled}
              title="无序列表"
            >
              <List className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleOrderedList().run()}
              isActive={editor?.isActive("orderedList")}
              disabled={disabled}
              title="有序列表"
            >
              <ListOrdered className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().toggleBlockquote().run()}
              isActive={editor?.isActive("blockquote")}
              disabled={disabled}
              title="引用"
            >
              <Quote className="h-4 w-4" />
            </ToolbarButton>

            <Separator orientation="vertical" className="mx-1 h-6" />

            <ToolbarButton
              onClick={() => editor?.chain().focus().undo().run()}
              disabled={disabled || !editor?.can().undo()}
              title="撤销"
            >
              <Undo className="h-4 w-4" />
            </ToolbarButton>
            <ToolbarButton
              onClick={() => editor?.chain().focus().redo().run()}
              disabled={disabled || !editor?.can().redo()}
              title="重做"
            >
              <Redo className="h-4 w-4" />
            </ToolbarButton>
          </div>
        </TooltipProvider>
      )}

      {/* 编辑器 */}
      <div
        className={cn(
          "rounded-lg border bg-background overflow-y-auto",
          disabled && "opacity-60 cursor-not-allowed"
        )}
        style={{ minHeight: minHeightStyle, maxHeight: maxHeightStyle }}
      >
        <EditorContent
          editor={editor}
          className={cn(
            "prose prose-sm dark:prose-invert max-w-none",
            "[&_.ProseMirror]:outline-none [&_.ProseMirror]:px-4 [&_.ProseMirror]:py-3",
            "[&_.ProseMirror]:min-h-[inherit]"
          )}
        />
      </div>

      {/* Markdown 预览 */}
      {showMarkdownPreview && (
        <details className="text-sm">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            查看 Markdown 输出
          </summary>
          <pre className="mt-2 max-h-[200px] overflow-auto rounded-lg bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
            {markdown}
          </pre>
        </details>
      )}
    </div>
  );
}

export const PromptEditor = memo(PromptEditorComponent);
PromptEditor.displayName = "PromptEditor";
