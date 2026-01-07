"use client";

import { EditorContent } from "@tiptap/react";
import React, { useCallback, useImperativeHandle, useRef } from "react";

import { cn } from "@/lib/utils";
import "./editor-styles.css";
import { Toolbar } from "./toolbar";
import type { FormattingCommand, RichEditorProps, RichEditorRef } from "./types";
import { useRichEditor } from "./use-rich-editor";

const RichEditor = React.forwardRef<RichEditorRef, RichEditorProps>(
  (
    {
      initialContent = "",
      placeholder = "输入内容...",
      onContentChange,
      onHtmlChange,
      onMarkdownChange,
      onBlur,
      editable = true,
      className = "",
      showToolbar = true,
      minHeight = 200,
      maxHeight,
      isFullWidth = true,
      fontSize = 14,
      enableSpellCheck = false,
    },
    ref
  ) => {
    const scrollContainerRef = useRef<HTMLDivElement>(null);

    const { editor, markdown, html, formattingState, setMarkdown, setHtml, clear, getPreviewText } =
      useRichEditor({
        initialContent,
        onChange: onMarkdownChange,
        onHtmlChange,
        onContentChange,
        onBlur,
        placeholder,
        editable,
        enableSpellCheck,
      });

    const handleCommand = useCallback(
      (command: FormattingCommand) => {
        if (!editor) return;

        switch (command) {
          case "bold":
            editor.chain().focus().toggleBold().run();
            break;
          case "italic":
            editor.chain().focus().toggleItalic().run();
            break;
          case "underline":
            editor.chain().focus().toggleUnderline().run();
            break;
          case "strike":
            editor.chain().focus().toggleStrike().run();
            break;
          case "code":
            editor.chain().focus().toggleCode().run();
            break;
          case "clearMarks":
            editor.chain().focus().unsetAllMarks().run();
            break;
          case "paragraph":
            editor.chain().focus().setParagraph().run();
            break;
          case "heading1":
            editor.chain().focus().toggleHeading({ level: 1 }).run();
            break;
          case "heading2":
            editor.chain().focus().toggleHeading({ level: 2 }).run();
            break;
          case "heading3":
            editor.chain().focus().toggleHeading({ level: 3 }).run();
            break;
          case "heading4":
            editor.chain().focus().toggleHeading({ level: 4 }).run();
            break;
          case "heading5":
            editor.chain().focus().toggleHeading({ level: 5 }).run();
            break;
          case "heading6":
            editor.chain().focus().toggleHeading({ level: 6 }).run();
            break;
          case "bulletList":
            editor.chain().focus().toggleBulletList().run();
            break;
          case "orderedList":
            editor.chain().focus().toggleOrderedList().run();
            break;
          case "codeBlock":
            editor.chain().focus().toggleCodeBlock().run();
            break;
          case "blockquote":
            editor.chain().focus().toggleBlockquote().run();
            break;
          case "link": {
            const previousUrl = editor.getAttributes("link").href;
            const url = window.prompt("输入链接地址", previousUrl);
            if (url === null) return;
            if (url === "") {
              editor.chain().focus().extendMarkRange("link").unsetLink().run();
              return;
            }
            editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
            break;
          }
          case "undo":
            editor.chain().focus().undo().run();
            break;
          case "redo":
            editor.chain().focus().redo().run();
            break;
          case "table":
            editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
            break;
          case "taskList":
            editor.chain().focus().toggleTaskList().run();
            break;
          case "image": {
            const url = window.prompt("输入图片地址");
            if (url) {
              editor.chain().focus().setImage({ src: url }).run();
            }
            break;
          }
        }
      },
      [editor]
    );

    // Expose editor methods via ref
    useImperativeHandle(
      ref,
      () => ({
        getContent: () => editor?.getText() || "",
        getHtml: () => html,
        getMarkdown: () => markdown,
        setContent: (content: string) => {
          editor?.commands.setContent(content);
        },
        setHtml: (htmlContent: string) => {
          setHtml(htmlContent);
        },
        setMarkdown: (markdownContent: string) => {
          setMarkdown(markdownContent);
        },
        focus: () => {
          editor?.commands.focus();
        },
        clear: () => {
          clear();
          editor?.commands.clearContent();
        },
        insertText: (text: string) => {
          editor?.commands.insertContent(text);
        },
        executeCommand: (command: string, value?: unknown) => {
          if (editor?.commands && command in editor.commands) {
            (editor.commands as Record<string, (v?: unknown) => void>)[command](value);
          }
        },
        getPreviewText: (maxLength?: number) => {
          return getPreviewText(markdown, maxLength);
        },
        getScrollTop: () => {
          return scrollContainerRef.current?.scrollTop ?? 0;
        },
        setScrollTop: (value: number) => {
          if (scrollContainerRef.current) {
            scrollContainerRef.current.scrollTop = value;
          }
        },
        // Dynamic command management (simplified for now)
        registerCommand: () => {},
        registerToolbarCommand: () => {},
        unregisterCommand: () => {},
        unregisterToolbarCommand: () => {},
        setCommandAvailability: () => {},
        getAllCommands: () => [],
        getToolbarCommands: () => [],
      }),
      [editor, html, markdown, setHtml, setMarkdown, clear, getPreviewText]
    );

    return (
      <div
        className={cn(
          "flex flex-col overflow-hidden rounded-md border border-zinc-200 bg-white dark:border-zinc-700 dark:bg-zinc-900",
          isFullWidth ? "w-full" : "mx-auto w-[60%]",
          className
        )}
        style={{
          minHeight: minHeight ? `${minHeight}px` : undefined,
          maxHeight: maxHeight ? `${maxHeight}px` : undefined,
          fontSize: `${fontSize}px`,
        }}
      >
        {showToolbar && (
          <Toolbar editor={editor} formattingState={formattingState} onCommand={handleCommand} />
        )}
        <div
          ref={scrollContainerRef}
          className="flex-1 overflow-y-auto"
          style={{ minHeight: minHeight ? `${minHeight - 50}px` : undefined }}
        >
          <EditorContent
            editor={editor}
            className="h-full"
          />
        </div>
      </div>
    );
  }
);

RichEditor.displayName = "RichEditor";

export default RichEditor;
export { RichEditor };
export type { RichEditorProps, RichEditorRef } from "./types";
