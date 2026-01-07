"use client";

import type { Editor } from "@tiptap/core";
import Highlight from "@tiptap/extension-highlight";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import Table from "@tiptap/extension-table";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import TableRow from "@tiptap/extension-table-row";
import TaskItem from "@tiptap/extension-task-item";
import TaskList from "@tiptap/extension-task-list";
import Underline from "@tiptap/extension-underline";
import { useEditor, useEditorState } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  htmlToMarkdown,
  isMarkdownContent,
  markdownToHtml,
  markdownToPreviewText,
} from "./helpers/markdown-converter";
import type { FormattingState } from "./types";

export interface UseRichEditorOptions {
  /** Initial markdown content */
  initialContent?: string;
  /** Callback when markdown content changes */
  onChange?: (markdown: string) => void;
  /** Callback when HTML content changes */
  onHtmlChange?: (html: string) => void;
  /** Callback when content changes (plain text) */
  onContentChange?: (content: string) => void;
  /** Callback when editor loses focus */
  onBlur?: () => void;
  /** Maximum length for preview text */
  previewLength?: number;
  /** Placeholder text when editor is empty */
  placeholder?: string;
  /** Whether the editor is editable */
  editable?: boolean;
  /** Whether to enable spell check */
  enableSpellCheck?: boolean;
}

export interface UseRichEditorReturn {
  /** TipTap editor instance */
  editor: Editor | null;
  /** Current markdown content */
  markdown: string;
  /** Current HTML content (converted from markdown) */
  html: string;
  /** Preview text for display */
  previewText: string;
  /** Whether content is detected as markdown */
  isMarkdown: boolean;
  /** Whether editor is disabled */
  disabled: boolean;
  /** Current formatting state from TipTap editor */
  formattingState: FormattingState;

  /** Set markdown content */
  setMarkdown: (content: string) => void;
  /** Set HTML content (converts to markdown) */
  setHtml: (html: string) => void;
  /** Clear all content */
  clear: () => void;

  /** Convert markdown to HTML */
  toHtml: (markdown: string) => string;
  /** Convert HTML to markdown */
  toMarkdown: (html: string) => string;
  /** Get preview text from markdown */
  getPreviewText: (markdown: string, maxLength?: number) => string;
}

/**
 * Custom hook for managing rich text content with Markdown storage
 */
export const useRichEditor = (options: UseRichEditorOptions = {}): UseRichEditorReturn => {
  const {
    initialContent = "",
    onChange,
    onHtmlChange,
    onContentChange,
    onBlur,
    previewLength = 50,
    placeholder = "",
    editable = true,
    enableSpellCheck = false,
  } = options;

  const [markdown, setMarkdownState] = useState<string>(initialContent);

  const html = useMemo(() => {
    if (!markdown) return "";
    return markdownToHtml(markdown);
  }, [markdown]);

  const previewText = useMemo(() => {
    if (!markdown) return "";
    return markdownToPreviewText(markdown, previewLength);
  }, [markdown, previewLength]);

  const isMarkdownDetected = useMemo(() => {
    return isMarkdownContent(markdown);
  }, [markdown]);

  // TipTap editor extensions
  const extensions = useMemo(
    () => [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3, 4, 5, 6],
        },
      }),
      Underline,
      Highlight.configure({
        multicolor: true,
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: "text-blue-600 underline hover:text-blue-800",
        },
      }),
      Image.configure({
        inline: false,
        allowBase64: true,
        HTMLAttributes: {
          class: "max-w-full rounded-lg",
        },
      }),
      Placeholder.configure({
        placeholder,
        showOnlyWhenEditable: true,
        showOnlyCurrent: true,
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
    ],
    [placeholder]
  );

  const editor = useEditor({
    extensions,
    content: html || "",
    editable,
    editorProps: {
      attributes: {
        spellcheck: enableSpellCheck ? "true" : "false",
        class:
          "prose prose-sm dark:prose-invert max-w-none focus:outline-none min-h-[120px] px-4 py-3",
      },
      handlePaste: (view, event) => {
        const text = event.clipboardData?.getData("text/plain") ?? "";
        if (text && isMarkdownContent(text)) {
          const htmlContent = markdownToHtml(text);
          view.pasteHTML(htmlContent);
          return true;
        }
        return false;
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      const content = currentEditor.getText();
      const htmlContent = currentEditor.getHTML();
      try {
        const convertedMarkdown = htmlToMarkdown(htmlContent);
        setMarkdownState(convertedMarkdown);
        onChange?.(convertedMarkdown);
        onContentChange?.(content);
        onHtmlChange?.(htmlContent);
      } catch (error) {
        console.error("Error converting HTML to markdown:", error);
      }
    },
    onBlur: () => {
      onBlur?.();
    },
  });

  useEffect(() => {
    if (editor && !editor.isDestroyed) {
      editor.setEditable(editable);
    }
  }, [editor, editable]);

  useEffect(() => {
    return () => {
      if (editor && !editor.isDestroyed) {
        editor.destroy();
      }
    };
  }, [editor]);

  const formattingState = useEditorState({
    editor,
    selector: ({ editor: currentEditor }): FormattingState => {
      if (!currentEditor || currentEditor.isDestroyed) {
        return {
          isBold: false,
          canBold: false,
          isItalic: false,
          canItalic: false,
          isUnderline: false,
          canUnderline: false,
          isStrike: false,
          canStrike: false,
          isCode: false,
          canCode: false,
          canClearMarks: false,
          isParagraph: false,
          isHeading1: false,
          isHeading2: false,
          isHeading3: false,
          isHeading4: false,
          isHeading5: false,
          isHeading6: false,
          isBulletList: false,
          isOrderedList: false,
          isCodeBlock: false,
          isBlockquote: false,
          isLink: false,
          canLink: false,
          canUndo: false,
          canRedo: false,
          isTable: false,
          canTable: false,
          canImage: false,
          isTaskList: false,
        };
      }

      return {
        isBold: currentEditor.isActive("bold") ?? false,
        canBold: currentEditor.can().chain().toggleBold().run() ?? false,
        isItalic: currentEditor.isActive("italic") ?? false,
        canItalic: currentEditor.can().chain().toggleItalic().run() ?? false,
        isUnderline: currentEditor.isActive("underline") ?? false,
        canUnderline: currentEditor.can().chain().toggleUnderline().run() ?? false,
        isStrike: currentEditor.isActive("strike") ?? false,
        canStrike: currentEditor.can().chain().toggleStrike().run() ?? false,
        isCode: currentEditor.isActive("code") ?? false,
        canCode: currentEditor.can().chain().toggleCode().run() ?? false,
        canClearMarks: currentEditor.can().chain().unsetAllMarks().run() ?? false,
        isParagraph: currentEditor.isActive("paragraph") ?? false,
        isHeading1: currentEditor.isActive("heading", { level: 1 }) ?? false,
        isHeading2: currentEditor.isActive("heading", { level: 2 }) ?? false,
        isHeading3: currentEditor.isActive("heading", { level: 3 }) ?? false,
        isHeading4: currentEditor.isActive("heading", { level: 4 }) ?? false,
        isHeading5: currentEditor.isActive("heading", { level: 5 }) ?? false,
        isHeading6: currentEditor.isActive("heading", { level: 6 }) ?? false,
        isBulletList: currentEditor.isActive("bulletList") ?? false,
        isOrderedList: currentEditor.isActive("orderedList") ?? false,
        isCodeBlock: currentEditor.isActive("codeBlock") ?? false,
        isBlockquote: currentEditor.isActive("blockquote") ?? false,
        isLink: currentEditor.isActive("link") ?? false,
        canLink: currentEditor.can().chain().setLink({ href: "" }).run() ?? false,
        canUndo: currentEditor.can().chain().undo().run() ?? false,
        canRedo: currentEditor.can().chain().redo().run() ?? false,
        isTable: currentEditor.isActive("table") ?? false,
        canTable:
          currentEditor.can().chain().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run() ??
          false,
        canImage: true,
        isTaskList: currentEditor.isActive("taskList") ?? false,
      };
    },
  });

  const setMarkdown = useCallback(
    (content: string) => {
      try {
        setMarkdownState(content);
        onChange?.(content);

        const convertedHtml = markdownToHtml(content);

        if (editor && !editor.isDestroyed) {
          editor.commands.setContent(convertedHtml);
        }

        onHtmlChange?.(convertedHtml);
      } catch (error) {
        console.error("Error setting markdown content:", error);
      }
    },
    [editor, onChange, onHtmlChange]
  );

  const setHtml = useCallback(
    (htmlContent: string) => {
      try {
        const convertedMarkdown = htmlToMarkdown(htmlContent);
        setMarkdownState(convertedMarkdown);
        onChange?.(convertedMarkdown);

        if (editor && !editor.isDestroyed) {
          editor.commands.setContent(htmlContent);
        }

        onHtmlChange?.(htmlContent);
      } catch (error) {
        console.error("Error setting HTML content:", error);
      }
    },
    [editor, onChange, onHtmlChange]
  );

  const clear = useCallback(() => {
    setMarkdownState("");
    onChange?.("");
    onHtmlChange?.("");
    if (editor && !editor.isDestroyed) {
      editor.commands.clearContent();
    }
  }, [editor, onChange, onHtmlChange]);

  const toHtml = useCallback((content: string): string => {
    try {
      return markdownToHtml(content);
    } catch (error) {
      console.error("Error converting markdown to HTML:", error);
      return "";
    }
  }, []);

  const toMarkdown = useCallback((htmlContent: string): string => {
    try {
      return htmlToMarkdown(htmlContent);
    } catch (error) {
      console.error("Error converting HTML to markdown:", error);
      return "";
    }
  }, []);

  const getPreviewText = useCallback(
    (content: string, maxLength?: number): string => {
      try {
        return markdownToPreviewText(content, maxLength || previewLength);
      } catch (error) {
        console.error("Error generating preview text:", error);
        return "";
      }
    },
    [previewLength]
  );

  return {
    editor,
    markdown,
    html,
    previewText,
    isMarkdown: isMarkdownDetected,
    disabled: !editable,
    formattingState: formattingState as FormattingState,
    setMarkdown,
    setHtml,
    clear,
    toHtml,
    toMarkdown,
    getPreviewText,
  };
};
