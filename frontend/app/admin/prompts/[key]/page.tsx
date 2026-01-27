"use client";

import { useCallback, useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  Loader2,
  RotateCcw,
  AlertCircle,
} from "lucide-react";
import { EditorContent } from "@tiptap/react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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

import { useRichEditor } from "@/components/rich-editor/use-rich-editor";
import { markdownToHtml } from "@/components/rich-editor/helpers/markdown-converter";
import "@/components/rich-editor/editor-styles.css";

import {
  getPrompt,
  updatePrompt,
  resetPrompt,
  Prompt,
  PROMPT_CATEGORY_LABELS,
  PROMPT_CATEGORY_COLORS,
} from "@/lib/api/prompts";

interface PageProps {
  params: Promise<{ key: string }>;
}

export default function PromptEditPage({ params }: PageProps) {
  const router = useRouter();
  const { key: encodedKey } = use(params);
  const promptKey = decodeURIComponent(encodedKey);

  const [prompt, setPrompt] = useState<Prompt | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 编辑状态
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  // 重置确认
  const [showResetDialog, setShowResetDialog] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  // 富文本编辑器
  const { editor, markdown, setMarkdown } = useRichEditor({
    initialContent: "",
    placeholder: "输入提示词内容...",
    editable: true,
    onChange: () => {
      setHasChanges(true);
    },
  });

  // 加载提示词
  const loadPrompt = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getPrompt(promptKey);
      setPrompt(data);
      setEditName(data.name);
      setEditDescription(data.description || "");

      // 设置编辑器内容
      if (editor && !editor.isDestroyed) {
        const html = markdownToHtml(data.content);
        editor.commands.setContent(html);
      }
      setHasChanges(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [promptKey, editor]);

  useEffect(() => {
    if (editor) {
      loadPrompt();
    }
  }, [editor, loadPrompt]);

  // 检测变更
  useEffect(() => {
    if (prompt) {
      const nameChanged = editName !== prompt.name;
      const descChanged = editDescription !== (prompt.description || "");
      const contentChanged = markdown !== prompt.content;
      setHasChanges(nameChanged || descChanged || contentChanged);
    }
  }, [editName, editDescription, markdown, prompt]);

  // 保存
  const handleSave = async () => {
    if (!prompt) return;

    try {
      setIsSaving(true);
      await updatePrompt(prompt.key, {
        name: editName,
        description: editDescription || undefined,
        content: markdown,
      });
      // 重新加载以获取最新状态
      await loadPrompt();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  // 重置
  const handleReset = async () => {
    if (!prompt) return;

    try {
      setIsResetting(true);
      await resetPrompt(prompt.key);
      setShowResetDialog(false);
      await loadPrompt();
    } catch (e) {
      setError(e instanceof Error ? e.message : "重置失败");
    } finally {
      setIsResetting(false);
    }
  };

  // 工具栏按钮
  const ToolbarButton = ({
    onClick,
    isActive,
    disabled,
    title,
    children,
  }: {
    onClick: () => void;
    isActive?: boolean;
    disabled?: boolean;
    title: string;
    children: React.ReactNode;
  }) => (
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

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !prompt) {
    return (
      <div className="container mx-auto max-w-4xl p-6">
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/admin/prompts">
            <ArrowLeft className="mr-2 h-4 w-4" />
            返回列表
          </Link>
        </Button>
      </div>
    );
  }

  if (!prompt) return null;

  const isCustom = prompt.source === "custom";
  const canReset = isCustom && prompt.default_content;

  return (
    <div className="container mx-auto max-w-4xl space-y-6 p-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/admin/prompts">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">编辑提示词</h1>
            <p className="text-sm text-muted-foreground font-mono">
              {prompt.key}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={PROMPT_CATEGORY_COLORS[prompt.category]}
          >
            {PROMPT_CATEGORY_LABELS[prompt.category]}
          </Badge>
          <Badge variant={isCustom ? "default" : "secondary"}>
            {isCustom ? "已自定义" : "默认"}
          </Badge>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* 基本信息 */}
      <Card>
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">名称</Label>
              <Input
                id="name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="提示词名称"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Input
                id="description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="提示词用途说明"
              />
            </div>
          </div>

          {prompt.variables.length > 0 && (
            <div className="space-y-2">
              <Label>支持的变量</Label>
              <div className="flex flex-wrap gap-2">
                {prompt.variables.map((v) => (
                  <Badge key={v} variant="outline" className="font-mono">
                    {"{" + v + "}"}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 内容编辑 */}
      <Card>
        <CardHeader>
          <CardTitle>提示词内容</CardTitle>
          <CardDescription>
            使用富文本编辑器编辑内容，支持 Markdown 格式
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 工具栏 */}
          <TooltipProvider delayDuration={300}>
            <div className="flex flex-wrap items-center gap-1 rounded-lg border bg-muted/30 p-1">
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleBold().run()}
                isActive={editor?.isActive("bold")}
                title="粗体"
              >
                <Bold className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleItalic().run()}
                isActive={editor?.isActive("italic")}
                title="斜体"
              >
                <Italic className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleCode().run()}
                isActive={editor?.isActive("code")}
                title="行内代码"
              >
                <Code className="h-4 w-4" />
              </ToolbarButton>

              <Separator orientation="vertical" className="mx-1 h-6" />

              <ToolbarButton
                onClick={() =>
                  editor?.chain().focus().toggleHeading({ level: 1 }).run()
                }
                isActive={editor?.isActive("heading", { level: 1 })}
                title="标题 1"
              >
                <Heading1 className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() =>
                  editor?.chain().focus().toggleHeading({ level: 2 }).run()
                }
                isActive={editor?.isActive("heading", { level: 2 })}
                title="标题 2"
              >
                <Heading2 className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() =>
                  editor?.chain().focus().toggleHeading({ level: 3 }).run()
                }
                isActive={editor?.isActive("heading", { level: 3 })}
                title="标题 3"
              >
                <Heading3 className="h-4 w-4" />
              </ToolbarButton>

              <Separator orientation="vertical" className="mx-1 h-6" />

              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleBulletList().run()}
                isActive={editor?.isActive("bulletList")}
                title="无序列表"
              >
                <List className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() =>
                  editor?.chain().focus().toggleOrderedList().run()
                }
                isActive={editor?.isActive("orderedList")}
                title="有序列表"
              >
                <ListOrdered className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() =>
                  editor?.chain().focus().toggleBlockquote().run()
                }
                isActive={editor?.isActive("blockquote")}
                title="引用"
              >
                <Quote className="h-4 w-4" />
              </ToolbarButton>

              <Separator orientation="vertical" className="mx-1 h-6" />

              <ToolbarButton
                onClick={() => editor?.chain().focus().undo().run()}
                disabled={!editor?.can().undo()}
                title="撤销"
              >
                <Undo className="h-4 w-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor?.chain().focus().redo().run()}
                disabled={!editor?.can().redo()}
                title="重做"
              >
                <Redo className="h-4 w-4" />
              </ToolbarButton>
            </div>
          </TooltipProvider>

          {/* 编辑器 */}
          <div className="rounded-lg border bg-background">
            <EditorContent
              editor={editor}
              className="min-h-[400px] max-h-[600px] overflow-y-auto prose prose-sm dark:prose-invert max-w-none [&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[380px] [&_.ProseMirror]:px-4 [&_.ProseMirror]:py-3"
            />
          </div>

          {/* Markdown 预览 */}
          <details className="text-sm">
            <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
              查看 Markdown 输出
            </summary>
            <pre className="mt-2 max-h-[200px] overflow-auto rounded-lg bg-muted p-3 font-mono text-xs">
              {markdown}
            </pre>
          </details>
        </CardContent>
      </Card>

      {/* 默认内容参考 */}
      {prompt.default_content && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">默认内容参考</CardTitle>
            <CardDescription>
              系统内置的默认提示词内容，可作为参考
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="max-h-[200px] overflow-auto rounded-lg bg-muted p-3 font-mono text-xs whitespace-pre-wrap">
              {prompt.default_content}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* 操作按钮 */}
      <div className="flex items-center justify-between">
        <div>
          {canReset && (
            <Button
              variant="outline"
              onClick={() => setShowResetDialog(true)}
              disabled={isSaving}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              重置为默认
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild disabled={isSaving}>
            <Link href="/admin/prompts">取消</Link>
          </Button>
          <Button onClick={handleSave} disabled={isSaving || !hasChanges}>
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-2 h-4 w-4" />
            )}
            保存
          </Button>
        </div>
      </div>

      {/* 重置确认对话框 */}
      <AlertDialog open={showResetDialog} onOpenChange={setShowResetDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认重置</AlertDialogTitle>
            <AlertDialogDescription>
              重置后将恢复为默认提示词内容，您的自定义修改将丢失。确定要重置吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isResetting}>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleReset} disabled={isResetting}>
              {isResetting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="mr-2 h-4 w-4" />
              )}
              重置
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
