"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ExternalLink, Loader2, Save, Settings, Sparkles, Wand2 } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  AGENT_TYPE_OPTIONS,
  createSkill,
  generateSkill,
  SkillCategory,
  SkillCreate,
  SKILL_CATEGORY_LABELS,
  SkillGenerateResponse,
} from "@/lib/api/skills";
import { getSystemConfig, type SystemConfigMasked } from "@/lib/api/system-config";

export default function GenerateSkillPage() {
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 系统配置（当前使用的模型）
  const [systemConfig, setSystemConfig] = useState<SystemConfigMasked | null>(null);

  // 输入数据
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<SkillCategory | "__auto__">("__auto__");
  const [applicableAgents, setApplicableAgents] = useState<string[]>([]);
  const [examples, setExamples] = useState("");

  // 生成结果
  const [result, setResult] = useState<SkillGenerateResponse | null>(null);

  // 加载系统配置
  const loadSystemConfig = useCallback(async () => {
    try {
      const config = await getSystemConfig();
      setSystemConfig(config);
    } catch (e) {
      console.error("加载系统配置失败", e);
    }
  }, []);

  useEffect(() => {
    loadSystemConfig();
  }, [loadSystemConfig]);

  const toggleAgent = (agent: string) => {
    setApplicableAgents((prev) =>
      prev.includes(agent) ? prev.filter((a) => a !== agent) : [...prev, agent]
    );
  };

  const handleGenerate = async () => {
    setError(null);

    if (description.length < 20) {
      setError("技能描述至少需要 20 个字符");
      return;
    }

    try {
      setIsGenerating(true);
      const res = await generateSkill({
        description,
        category: category === "__auto__" ? undefined : category,
        applicable_agents: applicableAgents.length > 0 ? applicableAgents : undefined,
        examples: examples
          ? examples.split("\n").filter((e) => e.trim())
          : undefined,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "生成失败");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!result) return;

    try {
      setIsSaving(true);
      await createSkill(result.skill);
      router.push("/admin/skills");
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="container mx-auto max-w-6xl space-y-6 p-6">
      {/* 页头 */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/admin/skills">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">AI 生成技能</h1>
          <p className="text-muted-foreground">
            描述你想要的技能，AI 将自动生成结构化定义
          </p>
        </div>
      </div>

      {/* 当前模型提示 */}
      {systemConfig && (
        <div className="flex items-center justify-between rounded-lg border bg-muted/50 px-4 py-3">
          <div className="flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-purple-500" />
            <span className="text-muted-foreground">当前 AI 模型：</span>
            <Badge variant="secondary" className="font-mono">
              {systemConfig.llm_chat_model}
            </Badge>
            <span className="text-muted-foreground">
              ({systemConfig.llm_provider})
            </span>
          </div>
          <Link
            href="/admin/settings/llm-config"
            className="flex items-center gap-1 text-sm text-primary hover:underline"
          >
            <Settings className="h-4 w-4" />
            配置模型
            <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 左侧：输入区 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5" />
              描述你的需求
            </CardTitle>
            <CardDescription>
              详细描述你想要的技能功能，AI 将根据描述生成技能定义
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="description">技能描述 *</Label>
              <Textarea
                id="description"
                placeholder="例如：我需要一个帮助用户对比多个商品的技能，能够分析商品的优劣势，列出价格、功能、评价等维度的对比表格，最后给出推荐建议..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={5}
              />
              <p className="text-xs text-muted-foreground">
                至少 20 个字符，当前 {description.length} 个
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">分类建议（可选）</Label>
              <Select
                value={category}
                onValueChange={(v) => setCategory(v as SkillCategory | "__auto__")}
              >
                <SelectTrigger id="category">
                  <SelectValue placeholder="由 AI 判断" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__auto__">由 AI 判断</SelectItem>
                  {Object.entries(SKILL_CATEGORY_LABELS).map(([value, label]) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>适用 Agent（可选）</Label>
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
              <Label htmlFor="examples">示例对话（可选）</Label>
              <Textarea
                id="examples"
                placeholder="用户: 这两个手机哪个好？&#10;用户: 帮我对比一下价格&#10;每行一条示例"
                value={examples}
                onChange={(e) => setExamples(e.target.value)}
                rows={3}
              />
            </div>

            <Button
              onClick={handleGenerate}
              disabled={description.length < 20 || isGenerating}
              className="w-full"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  生成技能
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* 右侧：预览区 */}
        <Card>
          <CardHeader>
            <CardTitle>生成结果</CardTitle>
            <CardDescription>
              {result
                ? `置信度: ${Math.round(result.confidence * 100)}%`
                : "输入描述后点击生成"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-4">
                <SkillPreview skill={result.skill} />

                {result.suggestions.length > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-2">
                      <Label className="text-amber-600">改进建议</Label>
                      <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                        {result.suggestions.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  </>
                )}

                <Separator />

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setResult(null)}
                  >
                    重新生成
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={handleSave}
                    disabled={isSaving}
                  >
                    {isSaving ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="mr-2 h-4 w-4" />
                    )}
                    保存技能
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="rounded-full bg-muted p-4">
                  <Sparkles className="h-8 w-8 text-muted-foreground" />
                </div>
                <p className="mt-4 text-sm text-muted-foreground">
                  在左侧输入描述后点击生成
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SkillPreview({ skill }: { skill: SkillCreate }) {
  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label className="text-muted-foreground">名称</Label>
        <p className="font-medium">{skill.name}</p>
      </div>

      <div className="space-y-1">
        <Label className="text-muted-foreground">描述</Label>
        <p className="text-sm">{skill.description}</p>
      </div>

      <div className="space-y-1">
        <Label className="text-muted-foreground">分类</Label>
        <Badge variant="outline">
          {SKILL_CATEGORY_LABELS[skill.category || "prompt"]}
        </Badge>
      </div>

      <div className="space-y-1">
        <Label className="text-muted-foreground">内容预览</Label>
        <div className="max-h-48 overflow-auto rounded-lg border bg-muted/50 p-3">
          <pre className="whitespace-pre-wrap text-xs">{skill.content}</pre>
        </div>
      </div>

      {skill.trigger_keywords && skill.trigger_keywords.length > 0 && (
        <div className="space-y-1">
          <Label className="text-muted-foreground">触发关键词</Label>
          <div className="flex flex-wrap gap-1">
            {skill.trigger_keywords.map((kw) => (
              <Badge key={kw} variant="secondary" className="text-xs">
                {kw}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {skill.applicable_agents && skill.applicable_agents.length > 0 && (
        <div className="space-y-1">
          <Label className="text-muted-foreground">适用 Agent</Label>
          <div className="flex flex-wrap gap-1">
            {skill.applicable_agents.map((a) => (
              <Badge key={a} variant="outline" className="text-xs">
                {AGENT_TYPE_OPTIONS.find((o) => o.value === a)?.label || a}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
