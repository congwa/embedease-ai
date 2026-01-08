"use client";

/**
 * Agent 专属 FAQ 管理页面
 * 
 * 仅展示和管理当前 Agent 绑定的 FAQ 条目
 * 包含统计视图、高级筛选、排序和来源展示
 */

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  Plus,
  Search,
  RefreshCw,
  Edit,
  Trash2,
  Check,
  X,
  Database,
  Filter,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import {
  getFAQEntries,
  getFAQStats,
  type FAQEntry,
  type FAQStatsResponse,
  type FAQListParams,
} from "@/lib/api/agents";

// 来源标签解析
function parseSource(source: string | null): string[] {
  if (!source) return [];
  return source.split(";").map((s) => s.trim()).filter(Boolean);
}

// 来源标签组件
function SourceTags({ source }: { source: string | null }) {
  const sources = parseSource(source);
  if (sources.length === 0) {
    return <span className="text-zinc-400">-</span>;
  }

  const displaySources = sources.slice(0, 2);
  const remainingSources = sources.slice(2);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <TooltipProvider>
      <div className="flex flex-wrap items-center gap-1">
        {displaySources.map((s, i) => (
          <Tooltip key={i}>
            <TooltipTrigger asChild>
              <Badge
                variant="outline"
                className="cursor-pointer text-xs"
                onClick={() => copyToClipboard(s)}
              >
                {s.length > 20 ? `${s.slice(0, 20)}...` : s}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              <p className="text-xs">{s}</p>
              <p className="text-xs text-zinc-400">点击复制</p>
            </TooltipContent>
          </Tooltip>
        ))}
        {remainingSources.length > 0 && (
          <Popover>
            <PopoverTrigger asChild>
              <Badge variant="secondary" className="cursor-pointer text-xs">
                +{remainingSources.length}
              </Badge>
            </PopoverTrigger>
            <PopoverContent className="w-64 p-2">
              <div className="space-y-1">
                <p className="text-xs font-medium text-zinc-500 mb-2">所有来源</p>
                {sources.map((s, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between rounded bg-zinc-50 px-2 py-1 text-xs dark:bg-zinc-800"
                  >
                    <span className="truncate flex-1">{s}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5 ml-1"
                      onClick={() => copyToClipboard(s)}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </PopoverContent>
          </Popover>
        )}
      </div>
    </TooltipProvider>
  );
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
  const [stats, setStats] = useState<FAQStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选状态
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [sourceFilter, setSourceFilter] = useState("");
  const [enabledFilter, setEnabledFilter] = useState<string>("all");
  const [priorityMin, setPriorityMin] = useState<string>("");
  const [priorityMax, setPriorityMax] = useState<string>("");
  const [orderBy, setOrderBy] = useState<FAQListParams["order_by"]>("updated_desc");

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

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const data = await getFAQStats(agentId);
      setStats(data);
    } catch (e) {
      console.error("加载统计失败", e);
    }
  }, [agentId]);

  // 加载 FAQ 列表
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const params: FAQListParams = {
        agent_id: agentId,
        order_by: orderBy,
      };

      if (selectedCategory !== "all") params.category = selectedCategory;
      if (sourceFilter) params.source = sourceFilter;
      if (enabledFilter === "true") params.enabled = true;
      if (enabledFilter === "false") params.enabled = false;
      if (priorityMin) params.priority_min = parseInt(priorityMin);
      if (priorityMax) params.priority_max = parseInt(priorityMax);

      const data = await getFAQEntries(params);
      setEntries(data || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [agentId, selectedCategory, sourceFilter, enabledFilter, priorityMin, priorityMax, orderBy]);

  useEffect(() => {
    loadData();
    loadStats();
  }, [loadData, loadStats]);

  // 获取分类列表（从统计数据获取）
  const categories = stats?.categories.map((c) => c.name) || [];

  // 本地搜索过滤
  const filteredEntries = entries.filter((entry) => {
    if (!searchQuery) return true;
    return (
      entry.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      entry.answer.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // 点击统计卡片快捷筛选
  const handleStatClick = (type: "unindexed" | "disabled") => {
    if (type === "unindexed") {
      setOrderBy("unindexed_first");
    } else if (type === "disabled") {
      setEnabledFilter("false");
    }
    setShowAdvancedFilters(true);
  };

  // 重置筛选
  const resetFilters = () => {
    setSelectedCategory("all");
    setSourceFilter("");
    setEnabledFilter("all");
    setPriorityMin("");
    setPriorityMax("");
    setOrderBy("updated_desc");
    setSearchQuery("");
  };

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
        ? "/api/v1/admin/faq?auto_merge=true"
        : `/api/v1/admin/faq/${editingEntry?.id}`;
      const method = isCreating ? "POST" : "PATCH";

      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("保存失败");

      // 处理创建时的合并结果
      if (isCreating) {
        const result = await response.json();
        if (result.merged) {
          alert(`已自动合并到 FAQ #${result.target_id?.slice(0, 8)}...`);
        } else {
          alert("新建 FAQ 成功");
        }
      }

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
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold">{stats?.total ?? "-"}</p>
              <p className="text-xs text-zinc-500">FAQ 总数</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">
                {stats?.enabled ?? "-"}
              </p>
              <p className="text-xs text-zinc-500">已启用</p>
            </div>
          </CardContent>
        </Card>
        <Card
          className="cursor-pointer hover:border-zinc-400 transition-colors"
          onClick={() => handleStatClick("disabled")}
        >
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-zinc-400">
                {stats?.disabled ?? "-"}
              </p>
              <p className="text-xs text-zinc-500">已禁用</p>
            </div>
          </CardContent>
        </Card>
        <Card
          className="cursor-pointer hover:border-amber-400 transition-colors"
          onClick={() => handleStatClick("unindexed")}
        >
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">
                {stats?.unindexed ?? "-"}
              </p>
              <p className="text-xs text-zinc-500">未索引</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-2xl font-bold">{stats?.categories.length ?? "-"}</p>
              <p className="text-xs text-zinc-500">分类数</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选栏 */}
      <div className="space-y-3">
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
            <SelectTrigger className="w-40">
              <SelectValue placeholder="选择分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部分类</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat} value={cat}>
                  {cat}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={orderBy} onValueChange={(v) => setOrderBy(v as FAQListParams["order_by"])}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="排序方式" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated_desc">最近更新</SelectItem>
              <SelectItem value="updated_asc">最早更新</SelectItem>
              <SelectItem value="priority_desc">优先级 高→低</SelectItem>
              <SelectItem value="priority_asc">优先级 低→高</SelectItem>
              <SelectItem value="unindexed_first">未索引优先</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          >
            <Filter className="mr-2 h-4 w-4" />
            高级筛选
            {showAdvancedFilters ? (
              <ChevronUp className="ml-1 h-4 w-4" />
            ) : (
              <ChevronDown className="ml-1 h-4 w-4" />
            )}
          </Button>
        </div>

        {/* 高级筛选面板 */}
        {showAdvancedFilters && (
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <Label className="text-xs">来源关键字</Label>
                <Input
                  placeholder="如 conversation: 或 chat:"
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">启用状态</Label>
                <Select value={enabledFilter} onValueChange={setEnabledFilter}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部</SelectItem>
                    <SelectItem value="true">已启用</SelectItem>
                    <SelectItem value="false">已禁用</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">优先级范围</Label>
                <div className="flex gap-2 mt-1">
                  <Input
                    type="number"
                    placeholder="最小"
                    value={priorityMin}
                    onChange={(e) => setPriorityMin(e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="最大"
                    value={priorityMax}
                    onChange={(e) => setPriorityMax(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex items-end">
                <Button variant="outline" size="sm" onClick={resetFilters}>
                  重置筛选
                </Button>
              </div>
            </div>
          </div>
        )}
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
              <TableHead className="w-[280px]">问题</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>来源</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>索引</TableHead>
              <TableHead>优先级</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">
                  <div className="flex items-center justify-center">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
                  </div>
                </TableCell>
              </TableRow>
            ) : filteredEntries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-zinc-500">
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
                    <SourceTags source={entry.source} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge enabled={entry.enabled} />
                  </TableCell>
                  <TableCell>
                    <VectorBadge vectorId={entry.vector_id} />
                  </TableCell>
                  <TableCell>
                    {entry.priority > 50 ? (
                      <Badge className="bg-orange-100 text-orange-700">{entry.priority}</Badge>
                    ) : (
                      <Badge variant="secondary">{entry.priority}</Badge>
                    )}
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
