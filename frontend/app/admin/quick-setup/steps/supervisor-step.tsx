"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, GripVertical, AlertCircle, Network, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { PromptEditor } from "@/components/admin";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { type StepProps } from "../page";
import {
  getSupervisorGlobalConfig,
  updateSupervisorGlobalConfig,
  getAvailableAgentsForSupervisor,
  type SupervisorSubAgent,
  type SupervisorGlobalConfig,
  type AvailableAgentForSupervisor,
} from "@/lib/api/admin";

const DEFAULT_SUPERVISOR_PROMPT = `你是一个智能助手调度器（Supervisor）。

你的职责是分析用户的问题，并将其路由到最合适的专业助手处理。

## 路由规则
1. 分析用户意图，选择最匹配的助手
2. 如果问题涉及多个领域，选择主要相关的助手
3. 如果无法确定，使用默认助手`;

export function SupervisorStep({ step, onComplete, isLoading }: StepProps) {
  const [availableAgents, setAvailableAgents] = useState<AvailableAgentForSupervisor[]>([]);
  const [subAgents, setSubAgents] = useState<SupervisorSubAgent[]>([]);
  const [routingPolicyType, setRoutingPolicyType] = useState<"keyword" | "intent" | "hybrid">("hybrid");
  const [defaultAgent, setDefaultAgent] = useState<string>("");
  const [supervisorPrompt, setSupervisorPrompt] = useState(DEFAULT_SUPERVISOR_PROMPT);
  const [loadingData, setLoadingData] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoadingData(true);
      const [config, agents] = await Promise.all([
        getSupervisorGlobalConfig(),
        getAvailableAgentsForSupervisor(),
      ]);

      setAvailableAgents(agents);

      // 从全局配置恢复
      if (config.sub_agents && config.sub_agents.length > 0) {
        setSubAgents(config.sub_agents);
      }
      if (config.routing_policy?.type) {
        setRoutingPolicyType(config.routing_policy.type as "keyword" | "intent" | "hybrid");
      }
      if (config.routing_policy?.default_agent_id) {
        setDefaultAgent(config.routing_policy.default_agent_id);
      }
      if (config.supervisor_prompt) {
        setSupervisorPrompt(config.supervisor_prompt);
      }

      // 也从步骤数据恢复（优先级更高）
      if (step.data) {
        if (step.data.sub_agents) {
          setSubAgents(step.data.sub_agents as SupervisorSubAgent[]);
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
    } catch (error) {
      console.error("加载 Supervisor 配置失败", error);
    } finally {
      setLoadingData(false);
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
        description: firstAvailable.description,
        routing_hints: [],
        priority: subAgents.length > 0 ? Math.max(...subAgents.map(s => s.priority)) - 10 : 100,
      },
    ]);
  };

  const handleRemoveSubAgent = (index: number) => {
    setSubAgents(subAgents.filter((_, i) => i !== index));
  };

  const handleSubAgentChange = (index: number, field: keyof SupervisorSubAgent, value: unknown) => {
    const updated = [...subAgents];
    if (field === "agent_id") {
      const selectedAgent = availableAgents.find(a => a.id === value);
      if (selectedAgent) {
        updated[index] = {
          ...updated[index],
          agent_id: value as string,
          name: selectedAgent.name,
          description: selectedAgent.description,
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
    try {
      setIsSaving(true);

      // 保存到全局 Supervisor 配置
      await updateSupervisorGlobalConfig({
        enabled: true,
        sub_agents: subAgents,
        routing_policy: {
          type: routingPolicyType,
          rules: [],
          default_agent_id: defaultAgent || null,
        },
        supervisor_prompt: supervisorPrompt,
      });

      // 完成步骤
      await onComplete({
        sub_agents: subAgents,
        routing_policy_type: routingPolicyType,
        default_agent: defaultAgent,
        supervisor_prompt: supervisorPrompt,
      });
    } catch (error) {
      console.error("保存 Supervisor 配置失败", error);
    } finally {
      setIsSaving(false);
    }
  };

  const canComplete = subAgents.length >= 1;

  if (loadingData) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary/10">
          <Network className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold">多 Agent 编排</h2>
          <p className="text-sm text-muted-foreground">
            配置全局 Supervisor 调度的子 Agent 和路由策略
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
              disabled={availableAgents.length === subAgents.length}
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
          <PromptEditor
            value={supervisorPrompt}
            onChange={setSupervisorPrompt}
            minHeight={180}
            maxHeight={350}
            placeholder={DEFAULT_SUPERVISOR_PROMPT}
          />
        </CardContent>
      </Card>

      {/* 完成按钮 */}
      <div className="flex justify-end">
        <Button onClick={handleComplete} disabled={!canComplete || isLoading || isSaving}>
          {isSaving ? "保存中..." : "保存并继续"}
        </Button>
      </div>
    </div>
  );
}
