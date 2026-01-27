"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check, Loader2, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PromptEditor } from "@/components/admin";
import { useAgentDetail } from "@/lib/hooks/use-agents";
import { updateAgent } from "@/lib/api/agents";

export default function AgentSystemPromptPage() {
  const params = useParams();
  const router = useRouter();
  const agentId = params.agentId as string;
  const { agent, refresh } = useAgentDetail({ agentId });

  const [editContent, setEditContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // 初始化编辑内容
  useEffect(() => {
    if (agent) {
      setEditContent(agent.system_prompt || "");
    }
  }, [agent]);

  // 检测变更
  useEffect(() => {
    if (agent) {
      setHasChanges(editContent !== (agent.system_prompt || ""));
    }
  }, [editContent, agent]);

  // 保存
  const handleSave = useCallback(async () => {
    if (!agent) return;

    try {
      setIsSaving(true);
      setError(null);
      await updateAgent(agent.id, {
        system_prompt: editContent,
      });
      await refresh();
      setHasChanges(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setIsSaving(false);
    }
  }, [agent, editContent, refresh]);

  if (!agent) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href={`/admin/agents/${agentId}`}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold">编辑系统提示词</h1>
            <p className="text-sm text-muted-foreground">
              {agent.name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild disabled={isSaving}>
            <Link href={`/admin/agents/${agentId}`}>取消</Link>
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

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {/* 编辑器 */}
      <Card>
        <CardHeader>
          <CardTitle>系统提示词</CardTitle>
          <CardDescription>
            定义 Agent 的角色、行为和回答风格，支持 Markdown 格式
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PromptEditor
            value={editContent}
            onChange={setEditContent}
            minHeight={400}
            maxHeight={600}
            placeholder="输入系统提示词内容..."
            showMarkdownPreview
          />
        </CardContent>
      </Card>
    </div>
  );
}
