"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Filter,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
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
  deleteSkill,
  listSkills,
  reloadSkillCache,
  Skill,
  SkillCategory,
  SKILL_CATEGORY_LABELS,
  SkillType,
  SKILL_TYPE_LABELS,
} from "@/lib/api/skills";

function SkillCard({
  skill,
  onDelete,
}: {
  skill: Skill;
  onDelete: (id: string) => void;
}) {
  const typeColors: Record<SkillType, string> = {
    system: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
    user: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
    ai: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
  };

  const categoryColors: Record<SkillCategory, string> = {
    prompt: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
    retrieval: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-300",
    tool: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300",
    workflow: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300",
  };

  return (
    <Card className="group relative overflow-hidden transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle className="text-lg">{skill.name}</CardTitle>
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="outline" className={typeColors[skill.type]}>
                {SKILL_TYPE_LABELS[skill.type]}
              </Badge>
              <Badge variant="outline" className={categoryColors[skill.category]}>
                {SKILL_CATEGORY_LABELS[skill.category]}
              </Badge>
              {skill.always_apply && (
                <Badge variant="secondary">始终应用</Badge>
              )}
              {!skill.is_active && (
                <Badge variant="destructive">已禁用</Badge>
              )}
            </div>
          </div>
          {!skill.is_system && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 opacity-0 transition-opacity group-hover:opacity-100"
              onClick={() => onDelete(skill.id)}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <CardDescription className="line-clamp-2">
          {skill.description}
        </CardDescription>

        {skill.trigger_keywords.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {skill.trigger_keywords.slice(0, 5).map((kw) => (
              <Badge key={kw} variant="outline" className="text-xs">
                {kw}
              </Badge>
            ))}
            {skill.trigger_keywords.length > 5 && (
              <Badge variant="outline" className="text-xs">
                +{skill.trigger_keywords.length - 5}
              </Badge>
            )}
          </div>
        )}

        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            适用: {skill.applicable_agents.length > 0
              ? skill.applicable_agents.join(", ")
              : "全部"}
          </span>
          <Link
            href={`/admin/skills/${skill.id}`}
            className="text-primary hover:underline"
          >
            查看详情 →
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);

  // 筛选条件
  const [typeFilter, setTypeFilter] = useState<SkillType | "all">("all");
  const [categoryFilter, setCategoryFilter] = useState<SkillCategory | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // 删除确认
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadSkills = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const result = await listSkills({
        type: typeFilter === "all" ? undefined : typeFilter,
        category: categoryFilter === "all" ? undefined : categoryFilter,
        page,
        page_size: pageSize,
      });

      // 本地搜索过滤
      let filtered = result.items;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filtered = filtered.filter(
          (s) =>
            s.name.toLowerCase().includes(query) ||
            s.description.toLowerCase().includes(query) ||
            s.trigger_keywords.some((kw) => kw.toLowerCase().includes(query))
        );
      }

      setSkills(filtered);
      setTotal(result.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [typeFilter, categoryFilter, page, pageSize, searchQuery]);

  useEffect(() => {
    loadSkills();
  }, [loadSkills]);

  const handleDelete = async () => {
    if (!deleteId) return;

    try {
      setIsDeleting(true);
      await deleteSkill(deleteId);
      setDeleteId(null);
      loadSkills();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleReloadCache = async () => {
    try {
      await reloadSkillCache();
      loadSkills();
    } catch (e) {
      setError(e instanceof Error ? e.message : "刷新缓存失败");
    }
  };

  return (
    <div className="container mx-auto max-w-7xl space-y-6 p-6">
      {/* 页头 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">技能管理</h1>
          <p className="text-muted-foreground">
            管理智能体的专业技能，支持自定义和 AI 生成
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleReloadCache}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新缓存
          </Button>
          <Button variant="outline" asChild>
            <Link href="/admin/skills/generate">
              <Sparkles className="mr-2 h-4 w-4" />
              AI 生成
            </Link>
          </Button>
          <Button asChild>
            <Link href="/admin/skills/create">
              <Plus className="mr-2 h-4 w-4" />
              创建技能
            </Link>
          </Button>
        </div>
      </div>

      {/* 筛选器 */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="搜索技能名称、描述或关键词..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select
            value={typeFilter}
            onValueChange={(v) => setTypeFilter(v as SkillType | "all")}
          >
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="system">系统内置</SelectItem>
              <SelectItem value="user">用户创建</SelectItem>
              <SelectItem value="ai">AI 生成</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={categoryFilter}
            onValueChange={(v) => setCategoryFilter(v as SkillCategory | "all")}
          >
            <SelectTrigger className="w-[130px]">
              <SelectValue placeholder="分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分类</SelectItem>
              <SelectItem value="prompt">提示词增强</SelectItem>
              <SelectItem value="retrieval">检索增强</SelectItem>
              <SelectItem value="tool">工具扩展</SelectItem>
              <SelectItem value="workflow">工作流</SelectItem>
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

      {/* 技能列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : skills.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full bg-muted p-4">
            <Sparkles className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="mt-4 text-lg font-medium">暂无技能</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            点击上方按钮创建新技能或使用 AI 生成
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {skills.map((skill) => (
              <SkillCard
                key={skill.id}
                skill={skill}
                onDelete={setDeleteId}
              />
            ))}
          </div>

          {/* 分页 */}
          {total > pageSize && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                上一页
              </Button>
              <span className="text-sm text-muted-foreground">
                第 {page} 页，共 {Math.ceil(total / pageSize)} 页
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= Math.ceil(total / pageSize)}
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </Button>
            </div>
          )}
        </>
      )}

      {/* 删除确认对话框 */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              删除后无法恢复，确定要删除这个技能吗？
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
