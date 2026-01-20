"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, GripVertical, AlertCircle, Network } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { type StepProps } from "../page";
import { getAgents, type Agent, type SubAgentConfig, type RoutingPolicy } from "@/lib/api/agents";

const DEFAULT_SUPERVISOR_PROMPT = `你是一个智能助手调度器（Supervisor）。

你的职责是分析用户的问题，并将其路由到最合适的专业助手处理。

## 路由规则
1. 分析用户意图，选择最匹配的助手
2. 如果问题涉及多个领域，选择主要相关的助手
3. 如果无法确定，使用默认助手`;

export function SupervisorStep({ step, state, onComplete, isLoading }: StepProps) {
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [subAgents, setSubAgents] = useState<SubAgentConfig[]>([]);
  const [routingPolicyType, setRoutingPolicyType] = useState<"keyword" | "intent" | "hybrid">("hybrid");
  const [defaultAgent, setDefaultAgent] = useState<string>("");
  const [supervisorPrompt, setSupervisorPrompt] = useState(DEFAULT_SUPERVISOR_PROMPT);
  const [loadingAgents, setLoadingAgents] = useState(true);

  useEffect(() => {
    loadAgents();
    // 从步骤数据恢复
    if (step.data) {
      if (step.data.sub_agents) {
        setSubAgents(step.data.sub_agents as SubAgentConfig[]);
      }
      if (step.data.routing_policy_type) {
        setRoutingPolicyType(step.data.routing_policy_type as typeof routingPolicyType);
      }
      if (step.data.default_agent) {
        setDefaultAgent(step.data.default_agent as string);
      }
      if (step.data.supervisor_prompt) {
        setSupervisorPrompt(step.data.supervisor_prompt as string);
      }
    }
  }, [step.data]);

  const loadAgents = async () => {
    try {
      const response = await getAgents({ status_filter: "enabled" });
      // 排除 supervisor 类型的 Agent（避免循环引用）
      const filtered = response.items.filter(a => !a.is_supervisor);
      setAvailableAgents(filtered);
    } catch (error) {
      console.error("加载 Agent 列表失败", error);
    } finally {
      setLoadingAgents(false);
    }
  };

  const handleAddSubAgent = () => {
    const firstAvailable = availableAgents.find(
      a => !subAgents.some(sa => sa.agent_id === a.id)
    );
    if (!firstAvailable) return;

    setSubAgents([
      ...subAgents,
      {
        agent_id: firstAvailable.id,
        name: firstAvailable.name,
        description: firstAvailable.description || "",
        routing_hints: [],
        priority: subAgents.length > 0 ? Math.max(...subAgents.map(s => s.priority)) - 10 : 100,
      },
    ]);
  };

  const handleRemoveSubAgent = (index: number) => {
    setSubAgents(subAgents.filter((_, i) => i !== index));
  };

  const handleSubAgentChange = (index: number, field: keyof SubAgentConfig, value: unknown) => {
    const updated = [...subAgents];
    if (field === "agent_id") {
      const selectedAgent = availableAgents.find(a => a.id === value);
      if (selectedAgent) {
        updated[index] = {
          ...updated[index],
          agent_id: value as string,
          name: selectedAgent.name,
          description: selectedAgent.description || "",
        };
      }
    } else if (field === "routing_hints") {
      updated[index] = {
        ...updated[index],
        routing_hints: (value as string).split(",").map(s => s.trim()).filter(Boolean),
      };
    } else {
      updated[index] = { ...updated[index], [field]: value };
    }
    setSubAgents(updated);
  };

  const handleComplete = async () => {
    // 构建路由策略
    const routingPolicy: RoutingPolicy = {
      type: routingPolicyType,
      rules: [],
      default_agent: defaultAgent || undefined,
      allow_multi_agent: false,
    };

    await onComplete({
      is_supervisor: true,
      sub_agents: subAgents,
      routing_policy: routingPolicy,
      supervisor_prompt: supervisorPrompt,
      routing_policy_type: routingPolicyType,
      default_agent: defaultAgent,
    });
  };

  const canComplete = subAgents.length >= 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <Network className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">多 Agent 编排</h2>
          <p className="text-sm text-muted-foreground">
            配置 Supervisor 调度的子 Agent 和路由策略
          </p>
        </div>
      </div>

      {/* 子 Agent 配置 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">子 Agent 列表</CardTitle>
              <CardDescription>选择要编排的 Agent</CardDescription>
            </div>
            <Button 
              onClick={handleAddSubAgent} 
              size="sm" 
              variant="outline"
              disabled={loadingAgents || availableAgents.length === subAgents.length}
            >
              <Plus className="w-4 h-4 mr-1" />
              添加
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {subAgents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>尚未添加子 Agent</p>
              <p className="text-sm">至少添加 1 个 Agent 才能继续</p>
            </div>
          ) : (
            subAgents.map((subAgent, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <GripVertical className="w-4 h-4 text-muted-foreground" />
                  <Badge variant="outline">#{index + 1}</Badge>
                  <div className="flex-1" />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleRemoveSubAgent(index)}
                  >
                    <Trash2 className="w-4 h-4 text-destructive" />
                  </Button>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>选择 Agent</Label>
                    <Select
                      value={subAgent.agent_id}
                      onValueChange={(v) => handleSubAgentChange(index, "agent_id", v)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availableAgents.map((a) => (
                          <SelectItem key={a.id} value={a.id}>
                            {a.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>优先级</Label>
                    <Input
                      type="number"
                      value={subAgent.priority}
                      onChange={(e) => handleSubAgentChange(index, "priority", Number(e.target.value))}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>路由提示关键词（逗号分隔）</Label>
                  <Input
                    placeholder="商品, 推荐, 价格"
                    value={subAgent.routing_hints.join(", ")}
                    onChange={(e) => handleSubAgentChange(index, "routing_hints", e.target.value)}
                  />
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* 路由策略 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">路由策略</CardTitle>
          <CardDescription>配置用户意图识别方式</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>策略类型</Label>
              <Select
                value={routingPolicyType}
                onValueChange={(v) => setRoutingPolicyType(v as typeof routingPolicyType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="keyword">关键词匹配</SelectItem>
                  <SelectItem value="intent">意图识别</SelectItem>
                  <SelectItem value="hybrid">混合模式（推荐）</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>默认 Agent</Label>
              <Select
                value={defaultAgent}
                onValueChange={setDefaultAgent}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择默认 Agent" />
                </SelectTrigger>
                <SelectContent>
                  {subAgents.map((sa) => (
                    <SelectItem key={sa.agent_id} value={sa.agent_id}>
                      {sa.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Alert>
            <AlertDescription>
              <strong>混合模式</strong>：先尝试关键词匹配，未命中时使用 LLM 意图识别
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Supervisor 提示词 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">调度提示词</CardTitle>
          <CardDescription>指导 Supervisor 如何分析意图和路由</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            value={supervisorPrompt}
            onChange={(e) => setSupervisorPrompt(e.target.value)}
            rows={8}
            className="font-mono text-sm"
          />
        </CardContent>
      </Card>

      {/* 完成按钮 */}
      <div className="flex justify-end">
        <Button onClick={handleComplete} disabled={!canComplete || isLoading}>
          {isLoading ? "保存中..." : "保存并继续"}
        </Button>
      </div>
    </div>
  );
}
