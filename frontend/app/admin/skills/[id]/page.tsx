"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Edit, Loader2, Save, Trash2 } from "lucide-react";
import Link from "next/link";

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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { PromptViewer, PromptEditor } from "@/components/admin";
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
  AGENT_TYPE_OPTIONS,
  deleteSkill,
  getSkill,
  Skill,
  SkillCategory,
  SKILL_CATEGORY_LABELS,
  SKILL_TYPE_LABELS,
  updateSkill,
} from "@/lib/api/skills";

export default function SkillDetailPage() {
  const params = useParams();
  const router = useRouter();
  const skillId = params.id as string;

  const [skill, setSkill] = useState<Skill | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // 编辑表单数据
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editCategory, setEditCategory] = useState<SkillCategory>("prompt");
  const [editContent, setEditContent] = useState("");
  const [editTriggerKeywords, setEditTriggerKeywords] = useState("");
  const [editAlwaysApply, setEditAlwaysApply] = useState(false);
  const [editApplicableAgents, setEditApplicableAgents] = useState<string[]>([]);
  const [editIsActive, setEditIsActive] = useState(true);

  const loadSkill = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await getSkill(skillId);
      setSkill(data);

      // 初始化编辑表单
      setEditName(data.name);
      setEditDescription(data.description);
      setEditCategory(data.category);
      setEditContent(data.content);
      setEditTriggerKeywords(data.trigger_keywords.join(", "));
      setEditAlwaysApply(data.always_apply);
      setEditApplicableAgents(data.applicable_agents);
      setEditIsActive(data.is_active);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [skillId]);

  useEffect(() => {
    loadSkill();
  }, [loadSkill]);

  const toggleAgent = (agent: string) => {
    setEditApplicableAgents((prev) =>
      prev.includes(agent) ? prev.filter((a) => a !== agent) : [...prev, agent]
    );
  };

  const handleSave = async () => {
    setError(null);

    if (!editName.trim()) {
      setError("请输入技能名称");
      return;
    }
    if (editDescription.length < 10) {
      setError("技能描述至少需要 10 个字符");
      return;
    }
    if (editContent.length < 10) {
      setError("技能内容至少需要 10 个字符");
      return;
    }

    try {
      setIsSaving(true);
      const updated = await updateSkill(skillId, {
        name: editName.trim(),
        description: editDescription.trim(),
        category: editCategory,
        content: editContent.trim(),
        trigger_keywords: editTriggerKeywords
          .split(/[,，\n]/)
          .map((k) => k.trim())
          .filter(Boolean),
        always_apply: editAlwaysApply,
        applicable_agents: editApplicableAgents,
        is_active: editIsActive,
      });
      setSkill(updated);
      setIsEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      setIsDeleting(true);
      await deleteSkill(skillId);
      router.push("/admin/skills");
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
      setShowDeleteDialog(false);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelEdit = () => {
    if (skill) {
      setEditName(skill.name);
      setEditDescription(skill.description);
      setEditCategory(skill.category);
      setEditContent(skill.content);
      setEditTriggerKeywords(skill.trigger_keywords.join(", "));
      setEditAlwaysApply(skill.always_apply);
      setEditApplicableAgents(skill.applicable_agents);
      setEditIsActive(skill.is_active);
    }
    setIsEditing(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!skill) {
    return (
      <div className="container mx-auto max-w-4xl p-6">
        <div className="text-center">
          <h2 className="text-xl font-semibold">技能不存在</h2>
          <p className="mt-2 text-muted-foreground">
            该技能可能已被删除
          </p>
          <Button asChild className="mt-4">
            <Link href="/admin/skills">返回列表</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl space-y-6 p-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/admin/skills">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{skill.name}</h1>
              <Badge variant="outline">
                {SKILL_TYPE_LABELS[skill.type]}
              </Badge>
              {!skill.is_active && <Badge variant="destructive">已禁用</Badge>}
            </div>
            <p className="text-muted-foreground">
              {skill.is_system ? "系统内置技能，不可修改" : "用户自定义技能"}
            </p>
          </div>
        </div>

        {!skill.is_system && (
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button variant="outline" onClick={handleCancelEdit}>
                  取消
                </Button>
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  保存
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </Button>
                <Button onClick={() => setIsEditing(true)}>
                  <Edit className="mr-2 h-4 w-4" />
                  编辑
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      {/* 基本信息 */}
      <Card>
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing ? (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>技能名称</Label>
                  <Input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>分类</Label>
                  <Select
                    value={editCategory}
                    onValueChange={(v) => setEditCategory(v as SkillCategory)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(SKILL_CATEGORY_LABELS).map(
                        ([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        )
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>描述</Label>
                <Textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={3}
                />
              </div>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label>启用状态</Label>
                  <p className="text-sm text-muted-foreground">
                    禁用后技能将不会被触发
                  </p>
                </div>
                <Switch
                  checked={editIsActive}
                  onCheckedChange={setEditIsActive}
                />
              </div>
            </>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label className="text-muted-foreground">分类</Label>
                  <p>{SKILL_CATEGORY_LABELS[skill.category]}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">版本</Label>
                  <p>{skill.version}</p>
                </div>
              </div>
              <div>
                <Label className="text-muted-foreground">描述</Label>
                <p>{skill.description}</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 text-sm text-muted-foreground">
                <div>创建时间: {new Date(skill.created_at).toLocaleString()}</div>
                <div>更新时间: {new Date(skill.updated_at).toLocaleString()}</div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 技能内容 */}
      <Card>
        <CardHeader>
          <CardTitle>技能内容</CardTitle>
          <CardDescription>技能的提示词内容</CardDescription>
        </CardHeader>
        <CardContent>
          {isEditing ? (
            <PromptEditor
              value={editContent}
              onChange={setEditContent}
              minHeight={300}
              maxHeight={500}
              placeholder="输入技能提示词内容..."
              showMarkdownPreview
            />
          ) : (
            <PromptViewer 
              content={skill.content} 
              maxHeight={400}
              onEdit={() => setIsEditing(true)}
              editLabel="编辑内容"
            />
          )}
        </CardContent>
      </Card>

      {/* 触发配置 */}
      <Card>
        <CardHeader>
          <CardTitle>触发配置</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing ? (
            <>
              <div className="space-y-2">
                <Label>触发关键词</Label>
                <Textarea
                  value={editTriggerKeywords}
                  onChange={(e) => setEditTriggerKeywords(e.target.value)}
                  rows={3}
                  placeholder="逗号分隔"
                />
              </div>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div className="space-y-0.5">
                  <Label>始终应用</Label>
                  <p className="text-sm text-muted-foreground">
                    开启后自动注入到系统提示词
                  </p>
                </div>
                <Switch
                  checked={editAlwaysApply}
                  onCheckedChange={setEditAlwaysApply}
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <Label className="text-muted-foreground">触发关键词</Label>
                <div className="mt-2 flex flex-wrap gap-1">
                  {skill.trigger_keywords.length > 0 ? (
                    skill.trigger_keywords.map((kw) => (
                      <Badge key={kw} variant="secondary">
                        {kw}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">无</span>
                  )}
                </div>
              </div>
              <Separator />
              <div className="flex items-center gap-2">
                <Label className="text-muted-foreground">始终应用:</Label>
                <Badge variant={skill.always_apply ? "default" : "outline"}>
                  {skill.always_apply ? "是" : "否"}
                </Badge>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 适用范围 */}
      <Card>
        <CardHeader>
          <CardTitle>适用范围</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isEditing ? (
            <>
              <div className="space-y-2">
                <Label>适用 Agent</Label>
                <div className="flex flex-wrap gap-2">
                  {AGENT_TYPE_OPTIONS.map((option) => (
                    <Badge
                      key={option.value}
                      variant={
                        editApplicableAgents.includes(option.value)
                          ? "default"
                          : "outline"
                      }
                      className="cursor-pointer"
                      onClick={() => toggleAgent(option.value)}
                    >
                      {option.label}
                    </Badge>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <Label className="text-muted-foreground">适用 Agent</Label>
                <div className="mt-2 flex flex-wrap gap-1">
                  {skill.applicable_agents.length > 0 ? (
                    skill.applicable_agents.map((a) => (
                      <Badge key={a} variant="outline">
                        {AGENT_TYPE_OPTIONS.find((o) => o.value === a)?.label ||
                          a}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">全部</span>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 删除确认对话框 */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              删除后无法恢复，确定要删除技能 "{skill.name}" 吗？
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
