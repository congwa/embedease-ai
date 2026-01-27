"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Save } from "lucide-react";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { PromptEditor } from "@/components/admin";
import {
  AGENT_TYPE_OPTIONS,
  createSkill,
  MODE_OPTIONS,
  SkillCategory,
  SKILL_CATEGORY_LABELS,
} from "@/lib/api/skills";

export default function CreateSkillPage() {
  const router = useRouter();
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 表单数据
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<SkillCategory>("prompt");
  const [content, setContent] = useState("");
  const [triggerKeywords, setTriggerKeywords] = useState("");
  const [alwaysApply, setAlwaysApply] = useState(false);
  const [applicableAgents, setApplicableAgents] = useState<string[]>([]);
  const [applicableModes, setApplicableModes] = useState<string[]>([]);

  const toggleAgent = (agent: string) => {
    setApplicableAgents((prev) =>
      prev.includes(agent) ? prev.filter((a) => a !== agent) : [...prev, agent]
    );
  };

  const toggleMode = (mode: string) => {
    setApplicableModes((prev) =>
      prev.includes(mode) ? prev.filter((m) => m !== mode) : [...prev, mode]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // 验证
    if (!name.trim()) {
      setError("请输入技能名称");
      return;
    }
    if (description.length < 10) {
      setError("技能描述至少需要 10 个字符");
      return;
    }
    if (content.length < 10) {
      setError("技能内容至少需要 10 个字符");
      return;
    }

    try {
      setIsSaving(true);
      await createSkill({
        name: name.trim(),
        description: description.trim(),
        category,
        content: content.trim(),
        trigger_keywords: triggerKeywords
          .split(/[,，\n]/)
          .map((k) => k.trim())
          .filter(Boolean),
        always_apply: alwaysApply,
        applicable_agents: applicableAgents,
        applicable_modes: applicableModes,
      });
      router.push("/admin/skills");
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl space-y-6 p-6">
      {/* 页头 */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/admin/skills">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">创建技能</h1>
          <p className="text-muted-foreground">定义新的智能体技能</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
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
            <CardDescription>设置技能的名称和描述</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">技能名称 *</Label>
                <Input
                  id="name"
                  placeholder="例如：商品对比专家"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={100}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="category">技能分类</Label>
                <Select
                  value={category}
                  onValueChange={(v) => setCategory(v as SkillCategory)}
                >
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(SKILL_CATEGORY_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">技能描述 *</Label>
              <Textarea
                id="description"
                placeholder="描述这个技能的用途和触发条件..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                至少 10 个字符，当前 {description.length} 个
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 技能内容 */}
        <Card>
          <CardHeader>
            <CardTitle>技能内容</CardTitle>
            <CardDescription>
              编写技能的提示词内容，使用 Markdown 格式
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>内容 *</Label>
              <PromptEditor
                value={content}
                onChange={setContent}
                minHeight={250}
                maxHeight={400}
                placeholder="## 技能名称&#10;&#10;### 规则&#10;1. 规则一&#10;2. 规则二&#10;&#10;### 输出格式&#10;..."
                showMarkdownPreview
              />
              <p className="text-xs text-muted-foreground">
                至少 10 个字符，当前 {content.length} 个
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 触发配置 */}
        <Card>
          <CardHeader>
            <CardTitle>触发配置</CardTitle>
            <CardDescription>设置技能的触发条件</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="keywords">触发关键词</Label>
              <Textarea
                id="keywords"
                placeholder="对比, 比较, 哪个好, VS&#10;每行一个或用逗号分隔"
                value={triggerKeywords}
                onChange={(e) => setTriggerKeywords(e.target.value)}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                用户消息包含这些关键词时触发技能
              </p>
            </div>

            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <Label htmlFor="always-apply">始终应用</Label>
                <p className="text-sm text-muted-foreground">
                  开启后技能将自动注入到 Agent 的系统提示词中
                </p>
              </div>
              <Switch
                id="always-apply"
                checked={alwaysApply}
                onCheckedChange={setAlwaysApply}
              />
            </div>
          </CardContent>
        </Card>

        {/* 适用范围 */}
        <Card>
          <CardHeader>
            <CardTitle>适用范围</CardTitle>
            <CardDescription>设置技能适用的 Agent 类型和模式</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>适用 Agent（留空表示全部）</Label>
              <div className="flex flex-wrap gap-2">
                {AGENT_TYPE_OPTIONS.map((option) => (
                  <Badge
                    key={option.value}
                    variant={
                      applicableAgents.includes(option.value)
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

            <div className="space-y-2">
              <Label>适用模式（留空表示全部）</Label>
              <div className="flex flex-wrap gap-2">
                {MODE_OPTIONS.map((option) => (
                  <Badge
                    key={option.value}
                    variant={
                      applicableModes.includes(option.value)
                        ? "default"
                        : "outline"
                    }
                    className="cursor-pointer"
                    onClick={() => toggleMode(option.value)}
                  >
                    {option.label}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 提交按钮 */}
        <div className="flex items-center justify-end gap-4">
          <Button variant="outline" asChild>
            <Link href="/admin/skills">取消</Link>
          </Button>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            创建技能
          </Button>
        </div>
      </form>
    </div>
  );
}
