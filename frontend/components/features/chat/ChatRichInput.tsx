"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EditorContent } from "@tiptap/react";
import { Bold, Italic, List, ListOrdered, Code, ArrowUp, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useMemo } from "react";
import { useRichEditor } from "@/components/rich-editor/use-rich-editor";
import { markdownToHtml } from "@/components/rich-editor/helpers/markdown-converter";
import "@/components/rich-editor/editor-styles.css";
import { useChatThemeOptional } from "@/components/features/chat/themes";

interface ChatRichInputProps {
  value: string;
  onValueChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  disabled?: boolean;
  isLoading?: boolean;
  className?: string;
}

export function ChatRichInput({
  value,
  onValueChange,
  onSubmit,
  placeholder = "输入消息...",
  disabled = false,
  isLoading = false,
  className,
}: ChatRichInputProps) {
  const theme = useChatThemeOptional();
  
  const { editor, markdown } = useRichEditor({
    initialContent: value,
    placeholder,
    editable: !disabled,
  });

  const lastExternalValue = useRef(value);

  useEffect(() => {
    if (value !== lastExternalValue.current && value !== markdown) {
      lastExternalValue.current = value;
      if (editor && !editor.isDestroyed) {
        if (!value) {
          editor.commands.clearContent();
        } else {
          // 将外部传入的 markdown 转为 HTML 再设置到编辑器
          const html = markdownToHtml(value);
          editor.commands.setContent(html);
        }
      }
    }
  }, [value, markdown, editor]);

  useEffect(() => {
    if (markdown !== lastExternalValue.current) {
      lastExternalValue.current = markdown;
      onValueChange(markdown);
    }
  }, [markdown, onValueChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (markdown.trim() && !isLoading) {
          onSubmit();
        }
      }
    },
    [markdown, isLoading, onSubmit]
  );

  const toggleBold = () => editor?.chain().focus().toggleBold().run();
  const toggleItalic = () => editor?.chain().focus().toggleItalic().run();
  const toggleBulletList = () => editor?.chain().focus().toggleBulletList().run();
  const toggleOrderedList = () => editor?.chain().focus().toggleOrderedList().run();
  const toggleCode = () => editor?.chain().focus().toggleCode().run();

  const canSubmit = markdown.trim().length > 0;

  // 使用主题系统获取类名，减少重复代码
  const inputWrapperClass = useMemo(
    () => theme?.getClass("inputWrapper") || "chat-default-input-wrapper",
    [theme]
  );

  const sendButtonClass = useMemo(() => {
    const base = theme?.getClass("sendButton") || "chat-default-send-btn";
    if (canSubmit) {
      const active = theme?.getClass("sendButtonActive") || "chat-default-send-btn-active";
      return `${base} ${active}`;
    }
    return base;
  }, [theme, canSubmit]);

  return (
    <div
      className={cn(
        "flex flex-col",
        inputWrapperClass,
        className
      )}
      onKeyDown={handleKeyDown}
    >
      <EditorContent
        editor={editor}
        className={cn(
          "chat-rich-editor flex-1 min-h-[40px] max-h-[200px] overflow-y-auto px-4 py-2",
          "prose prose-sm dark:prose-invert max-w-none",
          "focus-within:outline-none",
          "[&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[24px]",
          "[&_.ProseMirror_p.is-editor-empty:first-child::before]:text-[var(--chat-text-tertiary)]",
          "[&_.ProseMirror_p.is-editor-empty:first-child::before]:content-[attr(data-placeholder)]",
          "[&_.ProseMirror_p.is-editor-empty:first-child::before]:float-left",
          "[&_.ProseMirror_p.is-editor-empty:first-child::before]:pointer-events-none",
          "[&_.ProseMirror_p.is-editor-empty:first-child::before]:h-0"
        )}
      />
      
      <div className="flex items-center justify-between px-2 py-1.5 border-t border-[var(--chat-border-color)]">
        <TooltipProvider delayDuration={300}>
          <div className="flex items-center gap-0.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-[var(--chat-text-secondary)] hover:text-[var(--chat-text-primary)] hover:bg-[var(--chat-bg-user-bubble)]"
                  onClick={toggleBold}
                  disabled={disabled}
                >
                  <Bold className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">粗体</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-[var(--chat-text-secondary)] hover:text-[var(--chat-text-primary)] hover:bg-[var(--chat-bg-user-bubble)]"
                  onClick={toggleItalic}
                  disabled={disabled}
                >
                  <Italic className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">斜体</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-[var(--chat-text-secondary)] hover:text-[var(--chat-text-primary)] hover:bg-[var(--chat-bg-user-bubble)]"
                  onClick={toggleBulletList}
                  disabled={disabled}
                >
                  <List className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">无序列表</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-[var(--chat-text-secondary)] hover:text-[var(--chat-text-primary)] hover:bg-[var(--chat-bg-user-bubble)]"
                  onClick={toggleOrderedList}
                  disabled={disabled}
                >
                  <ListOrdered className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">有序列表</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-[var(--chat-text-secondary)] hover:text-[var(--chat-text-primary)] hover:bg-[var(--chat-bg-user-bubble)]"
                  onClick={toggleCode}
                  disabled={disabled}
                >
                  <Code className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">代码</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>

        <Button
          type="button"
          size="icon"
          className={cn("h-8 w-8", sendButtonClass)}
          onClick={onSubmit}
          disabled={!canSubmit || disabled}
        >
          {isLoading ? (
            <Square className="h-4 w-4" />
          ) : (
            <ArrowUp className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
