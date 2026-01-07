import type { Editor } from "@tiptap/core";
import type { LucideIcon } from "lucide-react";
import {
  Bold,
  CheckCircle,
  Code,
  FileCode,
  Heading1,
  Heading2,
  Heading3,
  Image,
  Italic,
  Link,
  List,
  ListOrdered,
  Minus,
  Quote,
  Redo,
  Strikethrough,
  Table,
  Type,
  Underline,
  Undo,
} from "lucide-react";

export interface Command {
  id: string;
  title: string;
  description: string;
  category: CommandCategory;
  icon: LucideIcon;
  keywords: string[];
  handler: (editor: Editor) => void;
  isAvailable?: (editor: Editor) => boolean;
  showInToolbar?: boolean;
  toolbarGroup?: "text" | "formatting" | "blocks" | "media" | "structure" | "history";
  formattingCommand?: string;
}

export enum CommandCategory {
  TEXT = "text",
  LISTS = "lists",
  BLOCKS = "blocks",
  MEDIA = "media",
  STRUCTURE = "structure",
  SPECIAL = "special",
}

const commandRegistry = new Map<string, Command>();

export function registerCommand(cmd: Command): void {
  commandRegistry.set(cmd.id, cmd);
}

export function unregisterCommand(id: string): void {
  commandRegistry.delete(id);
}

export function getCommand(id: string): Command | undefined {
  return commandRegistry.get(id);
}

export function getAllCommands(): Command[] {
  return Array.from(commandRegistry.values());
}

export function getToolbarCommands(): Command[] {
  return getAllCommands().filter((cmd) => cmd.showInToolbar);
}

export function registerToolbarCommand(cmd: Command): void {
  if (!cmd.showInToolbar) {
    cmd.showInToolbar = true;
  }
  registerCommand(cmd);
}

export function unregisterToolbarCommand(id: string): void {
  const cmd = getCommand(id);
  if (cmd) {
    cmd.showInToolbar = false;
  }
}

export function setCommandAvailability(id: string, isAvailable: (editor: Editor) => boolean): void {
  const cmd = getCommand(id);
  if (cmd) {
    cmd.isAvailable = isAvailable;
  }
}

export interface CommandFilterOptions {
  query?: string;
  category?: CommandCategory;
  maxResults?: number;
}

export function filterCommands(options: CommandFilterOptions = {}): Command[] {
  const { query = "", category } = options;

  let filtered = getAllCommands();

  if (category) {
    filtered = filtered.filter((cmd) => cmd.category === category);
  }

  if (query) {
    const searchTerm = query.toLowerCase().trim();
    filtered = filtered.filter((cmd) => {
      const searchableText = [cmd.title, cmd.description, ...cmd.keywords].join(" ").toLowerCase();
      return searchableText.includes(searchTerm);
    });

    filtered.sort((a, b) => {
      const aTitle = a.title.toLowerCase();
      const bTitle = b.title.toLowerCase();
      const aExactMatch = aTitle === searchTerm;
      const bExactMatch = bTitle === searchTerm;
      const aTitleMatch = aTitle.includes(searchTerm);
      const bTitleMatch = bTitle.includes(searchTerm);

      if (aExactMatch && !bExactMatch) return -1;
      if (bExactMatch && !aExactMatch) return 1;
      if (aTitleMatch && !bTitleMatch) return -1;
      if (bTitleMatch && !aTitleMatch) return 1;

      return a.title.localeCompare(b.title);
    });
  }

  return filtered;
}

const DEFAULT_COMMANDS: Command[] = [
  {
    id: "bold",
    title: "粗体",
    description: "将文本加粗",
    category: CommandCategory.TEXT,
    icon: Bold,
    keywords: ["bold", "strong", "粗体", "加粗"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleBold().run();
    },
    showInToolbar: true,
    toolbarGroup: "formatting",
    formattingCommand: "bold",
  },
  {
    id: "italic",
    title: "斜体",
    description: "将文本设为斜体",
    category: CommandCategory.TEXT,
    icon: Italic,
    keywords: ["italic", "emphasis", "斜体"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleItalic().run();
    },
    showInToolbar: true,
    toolbarGroup: "formatting",
    formattingCommand: "italic",
  },
  {
    id: "underline",
    title: "下划线",
    description: "为文本添加下划线",
    category: CommandCategory.TEXT,
    icon: Underline,
    keywords: ["underline", "下划线"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleUnderline().run();
    },
    showInToolbar: true,
    toolbarGroup: "formatting",
    formattingCommand: "underline",
  },
  {
    id: "strike",
    title: "删除线",
    description: "为文本添加删除线",
    category: CommandCategory.TEXT,
    icon: Strikethrough,
    keywords: ["strikethrough", "strike", "删除线"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleStrike().run();
    },
    showInToolbar: true,
    toolbarGroup: "formatting",
    formattingCommand: "strike",
  },
  {
    id: "inlineCode",
    title: "行内代码",
    description: "添加行内代码",
    category: CommandCategory.SPECIAL,
    icon: Code,
    keywords: ["code", "inline", "代码"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleCode().run();
    },
    showInToolbar: true,
    toolbarGroup: "formatting",
    formattingCommand: "code",
  },
  {
    id: "paragraph",
    title: "正文",
    description: "普通段落文本",
    category: CommandCategory.TEXT,
    icon: Type,
    keywords: ["text", "paragraph", "正文", "段落"],
    handler: (editor: Editor) => {
      editor.chain().focus().setParagraph().run();
    },
    showInToolbar: true,
    toolbarGroup: "text",
    formattingCommand: "paragraph",
  },
  {
    id: "heading1",
    title: "标题 1",
    description: "大标题",
    category: CommandCategory.TEXT,
    icon: Heading1,
    keywords: ["heading", "h1", "标题"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleHeading({ level: 1 }).run();
    },
    showInToolbar: true,
    toolbarGroup: "text",
    formattingCommand: "heading1",
  },
  {
    id: "heading2",
    title: "标题 2",
    description: "中标题",
    category: CommandCategory.TEXT,
    icon: Heading2,
    keywords: ["heading", "h2", "标题"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleHeading({ level: 2 }).run();
    },
    showInToolbar: true,
    toolbarGroup: "text",
    formattingCommand: "heading2",
  },
  {
    id: "heading3",
    title: "标题 3",
    description: "小标题",
    category: CommandCategory.TEXT,
    icon: Heading3,
    keywords: ["heading", "h3", "标题"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleHeading({ level: 3 }).run();
    },
    showInToolbar: true,
    toolbarGroup: "text",
    formattingCommand: "heading3",
  },
  {
    id: "bulletList",
    title: "无序列表",
    description: "创建无序列表",
    category: CommandCategory.LISTS,
    icon: List,
    keywords: ["bullet", "list", "无序列表"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleBulletList().run();
    },
    showInToolbar: true,
    toolbarGroup: "blocks",
    formattingCommand: "bulletList",
  },
  {
    id: "orderedList",
    title: "有序列表",
    description: "创建有序列表",
    category: CommandCategory.LISTS,
    icon: ListOrdered,
    keywords: ["number", "list", "有序列表"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleOrderedList().run();
    },
    showInToolbar: true,
    toolbarGroup: "blocks",
    formattingCommand: "orderedList",
  },
  {
    id: "taskList",
    title: "任务列表",
    description: "创建待办事项列表",
    category: CommandCategory.LISTS,
    icon: CheckCircle,
    keywords: ["task", "todo", "checklist", "任务"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleTaskList().run();
    },
    showInToolbar: true,
    toolbarGroup: "blocks",
    formattingCommand: "taskList",
  },
  {
    id: "codeBlock",
    title: "代码块",
    description: "插入代码块",
    category: CommandCategory.BLOCKS,
    icon: FileCode,
    keywords: ["code", "block", "代码块"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleCodeBlock().run();
    },
    showInToolbar: true,
    toolbarGroup: "blocks",
    formattingCommand: "codeBlock",
  },
  {
    id: "blockquote",
    title: "引用",
    description: "插入引用块",
    category: CommandCategory.BLOCKS,
    icon: Quote,
    keywords: ["quote", "blockquote", "引用"],
    handler: (editor: Editor) => {
      editor.chain().focus().toggleBlockquote().run();
    },
    showInToolbar: true,
    toolbarGroup: "blocks",
    formattingCommand: "blockquote",
  },
  {
    id: "divider",
    title: "分割线",
    description: "插入水平分割线",
    category: CommandCategory.STRUCTURE,
    icon: Minus,
    keywords: ["divider", "hr", "分割线"],
    handler: (editor: Editor) => {
      editor.chain().focus().setHorizontalRule().run();
    },
  },
  {
    id: "image",
    title: "图片",
    description: "插入图片",
    category: CommandCategory.MEDIA,
    icon: Image,
    keywords: ["image", "img", "图片"],
    handler: (editor: Editor) => {
      const url = window.prompt("输入图片地址");
      if (url) {
        editor.chain().focus().setImage({ src: url }).run();
      }
    },
    showInToolbar: true,
    toolbarGroup: "media",
    formattingCommand: "image",
  },
  {
    id: "link",
    title: "链接",
    description: "添加链接",
    category: CommandCategory.SPECIAL,
    icon: Link,
    keywords: ["link", "url", "链接"],
    handler: (editor: Editor) => {
      const previousUrl = editor.getAttributes("link").href;
      const url = window.prompt("输入链接地址", previousUrl);
      if (url === null) return;
      if (url === "") {
        editor.chain().focus().extendMarkRange("link").unsetLink().run();
        return;
      }
      editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
    },
    showInToolbar: true,
    toolbarGroup: "media",
    formattingCommand: "link",
  },
  {
    id: "table",
    title: "表格",
    description: "插入表格",
    category: CommandCategory.STRUCTURE,
    icon: Table,
    keywords: ["table", "表格"],
    handler: (editor: Editor) => {
      editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
    },
    showInToolbar: true,
    toolbarGroup: "structure",
    formattingCommand: "table",
  },
  {
    id: "undo",
    title: "撤销",
    description: "撤销上一步操作",
    category: CommandCategory.SPECIAL,
    icon: Undo,
    keywords: ["undo", "撤销"],
    handler: (editor: Editor) => {
      editor.chain().focus().undo().run();
    },
    showInToolbar: true,
    toolbarGroup: "history",
    formattingCommand: "undo",
  },
  {
    id: "redo",
    title: "重做",
    description: "重做上一步操作",
    category: CommandCategory.SPECIAL,
    icon: Redo,
    keywords: ["redo", "重做"],
    handler: (editor: Editor) => {
      editor.chain().focus().redo().run();
    },
    showInToolbar: true,
    toolbarGroup: "history",
    formattingCommand: "redo",
  },
];

// Initialize default commands
DEFAULT_COMMANDS.forEach(registerCommand);
