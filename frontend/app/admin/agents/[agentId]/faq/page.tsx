"use client";

/**
 * Agent 专属 FAQ 管理页面
 * 
 * 仅展示和管理当前 Agent 绑定的 FAQ 条目
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  HelpCircle,
  Plus,
  Search,
  RefreshCw,
  Edit,
  Trash2,
  Check,
  X,
  Database,
} from "lucide-react";
import { PageHeader, DataTablePagination } from "@/components/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAgentDetail } from "@/lib/hooks/use-agents";

interface FAQEntry {
  id: string;
  agent_id: string;
  question: string;
  answer: string;
  category: string | null;
  tags: string[] | null;
  enabled: boolean;
  priority: number;
  vector_id: string | null;
  created_at: string;
  updated_at: string;
}

function StatusBadge({ enabled }: { enabled: boolean }) {
  return enabled ? (
    <Badge variant="default" className="bg-green-100 text-green-700 hover:bg-green-100">
      <Check className="mr-1 h-3 w-3" />
      启用
    </Badge>
  ) : (
    <Badge variant="secondary" className="bg-zinc-100 text-zinc-500">
      <X className="mr-1 h-3 w-3" />
      禁用
    </Badge>
  );
}

function VectorBadge({ vectorId }: { vectorId: string | null }) {
  return vectorId ? (
    <Badge variant="outline" className="border-green-300 text-green-600">
      <Database className="mr-1 h-3 w-3" />
      已嵌入
    </Badge>
  ) : (
    <Badge variant="outline" className="border-amber-300 text-amber-600">
      待索引
    </Badge>
  );
}

export default function AgentFAQPage() {
  const params = useParams();
  const agentId = params.agentId as string;
  const { agent } = useAgentDetail({ agentId });

  const [entries, setEntries] = useState<FAQEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选状态
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  // 编辑状态
  const [editingEntry, setEditingEntry] = useState<FAQEntry | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState({
    question: "",
    answer: "",
    category: "",
    tags: "",
    priority: 0,
    enabled: true,
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`/api/v1/admin/faq?agent_id=${agentId}`);
      if (!response.ok) throw new Error("加载 FAQ 失败");

      const data = await response.json();
      setEntries(data || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 获取分类列表
  const categories = [...new Set(entries.map((e) => e.category).filter(Boolean))] as string[];

  // 筛选数据
  const filteredEntries = entries.filter((entry) => {
    const matchesSearch =
      !searchQuery ||
      entry.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.answer.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === "all" || entry.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleCreate = () => {
    setIsCreating(true);
    setEditingEntry(null);
    setFormData({
      question: "",
      answer: "",
      category: "",
      tags: "",
      priority: 0,
      enabled: true,
    });
    setIsSheetOpen(true);
  };

  const handleEdit = (entry: FAQEntry) => {
    setIsCreating(false);
    setEditingEntry(entry);
    setFormData({
      question: entry.question,
      answer: entry.answer,
      category: entry.category || "",
      tags: entry.tags?.join(", ") || "",
      priority: entry.priority,
      enabled: entry.enabled,
    });
    setIsSheetOpen(true);
  };

  const handleSave = async () => {
    try {
      const payload = {
        agent_id: agentId,
        question: formData.question,
        answer: formData.answer,
        category: formData.category || null,
        tags: formData.tags ? formData.tags.split(",").map((t) => t.trim()) : null,
        priority: formData.priority,
        enabled: formData.enabled,
      };

      const url = isCreating
        ? "/api/v1/admin/faq"
        : `/api/v1/admin/faq/${editingEntry?.id}`;
      const method = isCreating ? "POST" : "PATCH";

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("保存失败");

      setIsSheetOpen(false);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    }
  };

  const handleDelete = async (entryId: string) => {
    if (!confirm("确定要删除此 FAQ 条目吗？")) return;

    try {
      const response = await fetch(`/api/v1/admin/faq/${entryId}`, {
        method: "DELETE",
      });

      if (!response.ok) throw new Error("删除失败");
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  const handleRebuildIndex = async () => {
    try {
      const response = await fetch(
        `/api/v1/admin/faq/rebuild-index?agent_id=${agentId}`,
        { method: "POST" }
      );

      if (!response.ok) throw new Error("重建索引失败");
      alert("索引重建成功");
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "重建索引失败");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">FAQ 管理</h2>
          <p className="text-sm text-zinc-500">
            管理 {agent?.name || "此 Agent"} 的常见问题
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRebuildIndex}>
            <Database className="mr-2 h-4 w-4" />
            重建索引
          </Button>
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button size="sm" onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" />
            新建 FAQ
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold">{entries.length}</p>
              <p className="text-xs text-zinc-500">FAQ 总数</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {entries.filter((e) => e.enabled).length}
              </p>
              <p className="text-xs text-zinc-500">已启用</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">
                {entries.filter((e) => e.vector_id).length}
              </p>
              <p className="text-xs text-zinc-500">已索引</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold">{categories.length}</p>
              <p className="text-xs text-zinc-500">分类数</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选栏 */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <Input
            placeholder="搜索问题或答案..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="选择分类" />
          </SelectTrigger>
          <SelectContent>
            {/* SelectItem 不能使用空字符串作为 value，因为 Radix UI 使用空字符串来清空选择 */}
            <SelectItem value="all">全部分类</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* 表格 */}
      <div className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">问题</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>索引</TableHead>
              <TableHead>优先级</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center">
                  <div className="flex items-center justify-center">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredEntries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-zinc-500">
                  暂无 FAQ 数据
                </TableCell>
              </TableRow>
            ) : (
              filteredEntries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium line-clamp-2">{entry.question}</p>
                      <p className="text-xs text-zinc-500 line-clamp-1">
                        {entry.answer}
                      </p>
                    </div>
                  </TableCell>
                  <TableCell>
                    {entry.category ? (
                      <Badge variant="outline">{entry.category}</Badge>
                    ) : (
                      <span className="text-zinc-400">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusBadge enabled={entry.enabled} />
                  </TableCell>
                  <TableCell>
                    <VectorBadge vectorId={entry.vector_id} />
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary">{entry.priority}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleEdit(entry)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-red-600 hover:text-red-700"
                        onClick={() => handleDelete(entry.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* 编辑/创建面板 */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="w-[500px] sm:max-w-[500px]">
          <SheetHeader>
            <SheetTitle>{isCreating ? "新建 FAQ" : "编辑 FAQ"}</SheetTitle>
            <SheetDescription>
              {isCreating ? "添加新的常见问题" : "修改 FAQ 内容"}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            <div className="space-y-2">
              <Label>问题 *</Label>
              <Textarea
                value={formData.question}
                onChange={(e) =>
                  setFormData({ ...formData, question: e.target.value })
                }
                placeholder="输入问题..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label>答案 *</Label>
              <Textarea
                value={formData.answer}
                onChange={(e) =>
                  setFormData({ ...formData, answer: e.target.value })
                }
                placeholder="输入答案..."
                rows={6}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>分类</Label>
                <Input
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value })
                  }
                  placeholder="如：产品、售后"
                />
              </div>
              <div className="space-y-2">
                <Label>优先级</Label>
                <Input
                  type="number"
                  value={formData.priority}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      priority: parseInt(e.target.value) || 0,
                    })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>标签（逗号分隔）</Label>
              <Input
                value={formData.tags}
                onChange={(e) =>
                  setFormData({ ...formData, tags: e.target.value })
                }
                placeholder="如：退款,售后,物流"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled"
                checked={formData.enabled}
                onChange={(e) =>
                  setFormData({ ...formData, enabled: e.target.checked })
                }
                className="h-4 w-4 rounded border-zinc-300"
              />
              <Label htmlFor="enabled">启用此 FAQ</Label>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setIsSheetOpen(false)}>
                取消
              </Button>
              <Button onClick={handleSave}>保存</Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
