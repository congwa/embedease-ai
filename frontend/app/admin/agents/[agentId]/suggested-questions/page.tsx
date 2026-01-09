"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  Plus,
  Trash2,
  GripVertical,
  Edit2,
  Download,
  BarChart3,
  Loader2,
  Check,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  getSuggestedQuestions,
  createSuggestedQuestion,
  updateSuggestedQuestion,
  deleteSuggestedQuestion,
  importSuggestedQuestionsFromFAQ,
  reorderSuggestedQuestions,
  type SuggestedQuestion,
  type SuggestedQuestionCreate,
} from "@/lib/api/agents";

const SOURCE_LABELS: Record<string, string> = {
  manual: "手动",
  auto: "自动",
  faq: "FAQ",
};

const POSITION_LABELS: Record<string, string> = {
  welcome: "欢迎区",
  input: "输入框",
  both: "两处",
};

export default function SuggestedQuestionsPage() {
  const params = useParams();
  const agentId = params.agentId as string;

  const [questions, setQuestions] = useState<SuggestedQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // 对话框状态
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingQuestion, setEditingQuestion] = useState("");

  // 新增表单
  const [newQuestion, setNewQuestion] = useState("");
  const [newPosition, setNewPosition] = useState("both");

  // 导入表单
  const [importCategory, setImportCategory] = useState("");
  const [importLimit, setImportLimit] = useState(5);
  const [importPosition, setImportPosition] = useState("both");

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await getSuggestedQuestions(agentId);
      setQuestions(data);
    } catch (error) {
      console.error("加载推荐问题失败:", error);
    } finally {
      setIsLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 创建问题
  const handleCreate = async () => {
    if (!newQuestion.trim()) return;

    try {
      setIsSaving(true);
      await createSuggestedQuestion(agentId, {
        question: newQuestion.trim(),
        display_position: newPosition,
      });
      setNewQuestion("");
      setIsAddDialogOpen(false);
      await loadData();
    } catch (error) {
      console.error("创建失败:", error);
      alert("创建失败");
    } finally {
      setIsSaving(false);
    }
  };

  // 从 FAQ 导入
  const handleImport = async () => {
    try {
      setIsSaving(true);
      const imported = await importSuggestedQuestionsFromFAQ(agentId, {
        category: importCategory || undefined,
        limit: importLimit,
        display_position: importPosition,
      });
      setIsImportDialogOpen(false);
      await loadData();
      alert(`成功导入 ${imported.length} 条推荐问题`);
    } catch (error) {
      console.error("导入失败:", error);
      alert("导入失败，请确保有可用的 FAQ 条目");
    } finally {
      setIsSaving(false);
    }
  };

  // 更新问题
  const handleUpdate = async (id: string, data: Partial<SuggestedQuestionCreate>) => {
    try {
      await updateSuggestedQuestion(id, data);
      await loadData();
    } catch (error) {
      console.error("更新失败:", error);
    }
  };

  // 保存编辑
  const handleSaveEdit = async (id: string) => {
    if (!editingQuestion.trim()) return;
    await handleUpdate(id, { question: editingQuestion.trim() });
    setEditingId(null);
    setEditingQuestion("");
  };

  // 删除问题
  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除这个推荐问题吗？")) return;

    try {
      await deleteSuggestedQuestion(id);
      await loadData();
    } catch (error) {
      console.error("删除失败:", error);
    }
  };

  // 统计数据
  const stats = {
    total: questions.length,
    enabled: questions.filter((q) => q.enabled).length,
    welcome: questions.filter((q) => q.display_position !== "input").length,
    input: questions.filter((q) => q.display_position !== "welcome").length,
    totalClicks: questions.reduce((sum, q) => sum + q.click_count, 0),
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-zinc-500">总数</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-600">{stats.enabled}</div>
            <p className="text-xs text-zinc-500">已启用</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{stats.welcome}</div>
            <p className="text-xs text-zinc-500">欢迎区展示</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{stats.input}</div>
            <p className="text-xs text-zinc-500">输入框展示</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-orange-600">{stats.totalClicks}</div>
            <p className="text-xs text-zinc-500">总点击量</p>
          </CardContent>
        </Card>
      </div>

      {/* 操作栏 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div>
            <CardTitle className="text-base">推荐问题管理</CardTitle>
            <CardDescription>配置在聊天界面展示的推荐问题</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setIsImportDialogOpen(true)}>
              <Download className="mr-1.5 h-4 w-4" />
              从FAQ导入
            </Button>
            <Button size="sm" onClick={() => setIsAddDialogOpen(true)}>
              <Plus className="mr-1.5 h-4 w-4" />
              添加问题
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {questions.length === 0 ? (
            <div className="py-12 text-center text-zinc-500">
              <p className="mb-4">暂无推荐问题</p>
              <Button variant="outline" onClick={() => setIsAddDialogOpen(true)}>
                添加第一个问题
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50%]">问题</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>展示位置</TableHead>
                  <TableHead className="text-right">点击量</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {questions.map((q) => (
                  <TableRow key={q.id}>
                    <TableCell>
                      {editingId === q.id ? (
                        <div className="flex items-center gap-2">
                          <Input
                            value={editingQuestion}
                            onChange={(e) => setEditingQuestion(e.target.value)}
                            className="h-8"
                            autoFocus
                          />
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8"
                            onClick={() => handleSaveEdit(q.id)}
                          >
                            <Check className="h-4 w-4" />
                          </Button>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-8 w-8"
                            onClick={() => {
                              setEditingId(null);
                              setEditingQuestion("");
                            }}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ) : (
                        <span className="line-clamp-1">{q.question}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {SOURCE_LABELS[q.source] || q.source}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={q.display_position}
                        onValueChange={(value) =>
                          handleUpdate(q.id, { display_position: value })
                        }
                      >
                        <SelectTrigger className="h-8 w-24">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="welcome">欢迎区</SelectItem>
                          <SelectItem value="input">输入框</SelectItem>
                          <SelectItem value="both">两处</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {q.click_count}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={q.enabled}
                        onCheckedChange={(checked) =>
                          handleUpdate(q.id, { enabled: checked })
                        }
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          onClick={() => {
                            setEditingId(q.id);
                            setEditingQuestion(q.question);
                          }}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8 text-red-500 hover:text-red-600"
                          onClick={() => handleDelete(q.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 添加对话框 */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加推荐问题</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>问题内容</Label>
              <Input
                value={newQuestion}
                onChange={(e) => setNewQuestion(e.target.value)}
                placeholder="输入推荐问题..."
                maxLength={200}
              />
            </div>
            <div className="space-y-2">
              <Label>展示位置</Label>
              <Select value={newPosition} onValueChange={setNewPosition}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="both">两处都展示</SelectItem>
                  <SelectItem value="welcome">仅欢迎区</SelectItem>
                  <SelectItem value="input">仅输入框上方</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreate} disabled={!newQuestion.trim() || isSaving}>
              {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 导入对话框 */}
      <Dialog open={isImportDialogOpen} onOpenChange={setIsImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>从 FAQ 导入</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>FAQ 分类（可选）</Label>
              <Input
                value={importCategory}
                onChange={(e) => setImportCategory(e.target.value)}
                placeholder="留空则导入所有分类"
              />
            </div>
            <div className="space-y-2">
              <Label>导入数量</Label>
              <Select
                value={String(importLimit)}
                onValueChange={(v) => setImportLimit(Number(v))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="3">3 条</SelectItem>
                  <SelectItem value="5">5 条</SelectItem>
                  <SelectItem value="10">10 条</SelectItem>
                  <SelectItem value="20">20 条</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>展示位置</Label>
              <Select value={importPosition} onValueChange={setImportPosition}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="both">两处都展示</SelectItem>
                  <SelectItem value="welcome">仅欢迎区</SelectItem>
                  <SelectItem value="input">仅输入框上方</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsImportDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleImport} disabled={isSaving}>
              {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              导入
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
