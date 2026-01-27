"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Edit2,
  Filter,
  Loader2,
  RotateCcw,
  Search,
  FileText,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import {
  listPrompts,
  resetPrompt,
  Prompt,
  PromptCategory,
  PROMPT_CATEGORY_LABELS,
  PROMPT_CATEGORY_COLORS,
  PROMPT_SOURCE_LABELS,
} from "@/lib/api/prompts";

function PromptCard({
  prompt,
  onReset,
}: {
  prompt: Prompt;
  onReset: (key: string) => void;
}) {
  const router = useRouter();
  const isCustom = prompt.source === "custom";

  const handleEdit = () => {
    router.push(`/admin/prompts/${encodeURIComponent(prompt.key)}`);
  };

  return (
    <Card className="group relative overflow-hidden transition-shadow hover:shadow-md cursor-pointer" onClick={handleEdit}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1 min-w-0">
            <CardTitle className="text-lg truncate">{prompt.name}</CardTitle>
            <div className="flex flex-wrap gap-1.5">
              <Badge
                variant="outline"
                className={PROMPT_CATEGORY_COLORS[prompt.category]}
              >
                {PROMPT_CATEGORY_LABELS[prompt.category]}
              </Badge>
              <Badge
                variant={isCustom ? "default" : "secondary"}
                className={isCustom ? "bg-amber-500" : ""}
              >
                {PROMPT_SOURCE_LABELS[prompt.source]}
              </Badge>
              {!prompt.is_active && (
                <Badge variant="destructive">已禁用</Badge>
              )}
            </div>
          </div>
          <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={(e) => {
                e.stopPropagation();
                handleEdit();
              }}
            >
              <Edit2 className="h-4 w-4" />
            </Button>
            {isCustom && prompt.default_content && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation();
                  onReset(prompt.key);
                }}
                title="重置为默认值"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <CardDescription className="line-clamp-2">
          {prompt.description || "暂无描述"}
        </CardDescription>

        <div className="text-xs text-muted-foreground font-mono bg-muted/50 p-2 rounded line-clamp-3">
          {prompt.content.slice(0, 150)}
          {prompt.content.length > 150 && "..."}
        </div>

        {prompt.variables.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <span className="text-xs text-muted-foreground">变量：</span>
            {prompt.variables.map((v) => (
              <Badge key={v} variant="outline" className="text-xs font-mono">
                {"{" + v + "}"}
              </Badge>
            ))}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span className="font-mono">{prompt.key}</span>
          {prompt.updated_at && (
            <span>
              更新于 {new Date(prompt.updated_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选条件
  const [categoryFilter, setCategoryFilter] = useState<PromptCategory | "all">(
    "all"
  );
  const [searchQuery, setSearchQuery] = useState("");

  // 重置确认
  const [resetKey, setResetKey] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  const loadPrompts = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await listPrompts({
        category: categoryFilter === "all" ? undefined : categoryFilter,
      });

      // 本地搜索过滤
      let filtered = result.items;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filtered = filtered.filter(
          (p) =>
            p.name.toLowerCase().includes(query) ||
            p.key.toLowerCase().includes(query) ||
            p.description?.toLowerCase().includes(query) ||
            p.content.toLowerCase().includes(query)
        );
      }

      setPrompts(filtered);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [categoryFilter, searchQuery]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handleReset = async () => {
    if (!resetKey) return;

    try {
      setIsResetting(true);
      await resetPrompt(resetKey);
      setResetKey(null);
      loadPrompts();
    } catch (e) {
      setError(e instanceof Error ? e.message : "重置失败");
    } finally {
      setIsResetting(false);
    }
  };


  return (
    <div className="container mx-auto max-w-7xl space-y-6 p-6">
      {/* 页头 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">提示词管理</h1>
          <p className="text-muted-foreground">
            统一管理系统中的所有提示词模板，支持自定义和重置
          </p>
        </div>
      </div>

      {/* 筛选器 */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索提示词名称、key 或内容..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select
            value={categoryFilter}
            onValueChange={(v) =>
              setCategoryFilter(v as PromptCategory | "all")
            }
          >
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分类</SelectItem>
              <SelectItem value="agent">Agent 提示词</SelectItem>
              <SelectItem value="memory">记忆系统</SelectItem>
              <SelectItem value="skill">技能生成</SelectItem>
              <SelectItem value="crawler">爬虫提取</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* 提示词列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : prompts.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4">
            <FileText className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="mt-4 text-lg font-medium">暂无提示词</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            未找到匹配的提示词
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {prompts.map((prompt) => (
            <PromptCard
              key={prompt.key}
              prompt={prompt}
              onReset={setResetKey}
            />
          ))}
        </div>
      )}

      {/* 重置确认对话框 */}
      <AlertDialog open={!!resetKey} onOpenChange={() => setResetKey(null)}>
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
