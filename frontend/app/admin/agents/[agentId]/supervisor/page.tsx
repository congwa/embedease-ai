"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Plus, Trash2, GripVertical, AlertCircle } from "lucide-react";
import { useAgentDetail, useAgents } from "@/lib/hooks/use-agents";
import { updateAgent, type SubAgentConfig, type RoutingPolicy, type RoutingRule } from "@/lib/api/agents";
import { LoadingState } from "@/components/admin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";

const DEFAULT_SUPERVISOR_PROMPT = `你是一个智能助手调度器（Supervisor）。

你的职责是分析用户的问题，并将其路由到最合适的专业助手处理。

## 路由规则
1. 分析用户意图，选择最匹配的助手
2. 如果问题涉及多个领域，选择主要相关的助手
3. 如果无法确定，使用默认助手`;

export default function SupervisorPage() {
  const params = useParams();
  const agentId = params.agentId as string;
  
  const { agent, isLoading, refresh } = useAgentDetail({ agentId });
  const { agents: allAgents } = useAgents();
  
  const [isSupervisor, setIsSupervisor] = useState(false);
  const [subAgents, setSubAgents] = useState<SubAgentConfig[]>([]);
  const [routingPolicy, setRoutingPolicy] = useState<RoutingPolicy>({
    type: "hybrid",
    rules: [],
    default_agent: undefined,
    allow_multi_agent: false,
  });
  const [supervisorPrompt, setSupervisorPrompt] = useState(DEFAULT_SUPERVISOR_PROMPT);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // 可选的子 Agent 列表（排除自己）
  const availableAgents = allAgents?.filter(a => a.id !== agentId && a.status === "enabled") || [];

  useEffect(() => {
    if (agent) {
      setIsSupervisor(agent.is_supervisor || false);
      setSubAgents(agent.sub_agents || []);
      setRoutingPolicy(agent.routing_policy || {
        type: "hybrid",
        rules: [],
        default_agent: undefined,
        allow_multi_agent: false,
      });
      setSupervisorPrompt(agent.supervisor_prompt || DEFAULT_SUPERVISOR_PROMPT);
    }
  }, [agent]);

  const handleAddSubAgent = () => {
    if (availableAgents.length === 0) return;
    
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

  const handleAddRule = () => {
    setRoutingPolicy({
      ...routingPolicy,
      rules: [
        ...routingPolicy.rules,
        {
          condition: { type: "keyword", keywords: [] },
          target: subAgents[0]?.agent_id || "",
          priority: routingPolicy.rules.length > 0 
            ? Math.max(...routingPolicy.rules.map(r => r.priority)) + 10 
            : 100,
        },
      ],
    });
  };

  const handleRemoveRule = (index: number) => {
    setRoutingPolicy({
      ...routingPolicy,
      rules: routingPolicy.rules.filter((_, i) => i !== index),
    });
  };

  const handleRuleChange = (index: number, field: string, value: unknown) => {
    const updated = [...routingPolicy.rules];
    if (field === "keywords") {
      updated[index] = {
        ...updated[index],
        condition: {
          ...updated[index].condition,
          keywords: (value as string).split(",").map(s => s.trim()).filter(Boolean),
        },
      };
    } else if (field === "intents") {
      updated[index] = {
        ...updated[index],
        condition: {
          ...updated[index].condition,
          intents: (value as string).split(",").map(s => s.trim()).filter(Boolean),
        },
      };
    } else if (field === "condition_type") {
      updated[index] = {
        ...updated[index],
        condition: {
          type: value as "keyword" | "intent",
          keywords: value === "keyword" ? [] : undefined,
          intents: value === "intent" ? [] : undefined,
        },
      };
    } else if (field === "target") {
      updated[index] = { ...updated[index], target: value as string };
    } else if (field === "priority") {
      updated[index] = { ...updated[index], priority: Number(value) };
    }
    setRoutingPolicy({ ...routingPolicy, rules: updated });
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus(null);

    try {
      await updateAgent(agentId, {
        is_supervisor: isSupervisor,
        sub_agents: isSupervisor ? subAgents : null,
        routing_policy: isSupervisor ? routingPolicy : null,
        supervisor_prompt: isSupervisor ? supervisorPrompt : null,
      });
      setSaveStatus({ type: "success", message: "保存成功" });
      refresh();
    } catch (error) {
      setSaveStatus({ type: "error", message: `保存失败: ${error}` });
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return <LoadingState text="加载中..." />;
  }

  return (
    <div className="space-y-6">
      {/* 状态提示 */}
      {saveStatus && (
        <Alert variant={saveStatus.type === "error" ? "destructive" : "default"}>
          <AlertDescription>{saveStatus.message}</AlertDescription>
        </Alert>
      )}

      {/* Supervisor 开关 */}
      <Card>
        <CardHeader>
          <CardTitle>Supervisor 模式</CardTitle>
          <CardDescription>
            启用后，此 Agent 将作为调度器，根据用户意图自动路由到子 Agent 处理
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Switch
              checked={isSupervisor}
              onCheckedChange={setIsSupervisor}
            />
            <Label>{isSupervisor ? "已启用" : "未启用"}</Label>
            {isSupervisor && (
              <Badge variant="secondary">多 Agent 编排</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {isSupervisor && (
        <>
          {/* 子 Agent 配置 */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>子 Agent 列表</CardTitle>
                  <CardDescription>配置 Supervisor 可调度的子 Agent</CardDescription>
                </div>
                <Button onClick={handleAddSubAgent} size="sm" variant="outline">
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
                  <p className="text-sm">点击上方按钮添加可调度的 Agent</p>
                </div>
              ) : (
                subAgents.map((subAgent, index) => (
                  <div key={index} className="border rounded-lg p-4 space-y-3">
                    <div className="flex items-center gap-2">
                      <GripVertical className="w-4 h-4 text-muted-foreground cursor-move" />
                      <span className="font-medium">#{index + 1}</span>
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
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>路由策略</CardTitle>
                  <CardDescription>配置用户意图到 Agent 的路由规则</CardDescription>
                </div>
                <Button onClick={handleAddRule} size="sm" variant="outline" disabled={subAgents.length === 0}>
                  <Plus className="w-4 h-4 mr-1" />
                  添加规则
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>策略类型</Label>
                  <Select
                    value={routingPolicy.type}
                    onValueChange={(v) => setRoutingPolicy({ ...routingPolicy, type: v as RoutingPolicy["type"] })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="keyword">关键词匹配</SelectItem>
                      <SelectItem value="intent">意图识别</SelectItem>
                      <SelectItem value="hybrid">混合（推荐）</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>默认 Agent</Label>
                  <Select
                    value={routingPolicy.default_agent || ""}
                    onValueChange={(v) => setRoutingPolicy({ ...routingPolicy, default_agent: v || undefined })}
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

              {/* 规则列表 */}
              {routingPolicy.rules.length > 0 && (
                <div className="space-y-3 mt-4">
                  <Label>路由规则</Label>
                  {routingPolicy.rules.map((rule, index) => (
                    <div key={index} className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">规则 {index + 1}</Badge>
                        <div className="flex-1" />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveRule(index)}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </div>

                      <div className="grid grid-cols-3 gap-3">
                        <div className="space-y-1">
                          <Label className="text-xs">条件类型</Label>
                          <Select
                            value={rule.condition.type}
                            onValueChange={(v) => handleRuleChange(index, "condition_type", v)}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="keyword">关键词</SelectItem>
                              <SelectItem value="intent">意图</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs">
                            {rule.condition.type === "keyword" ? "关键词" : "意图"}（逗号分隔）
                          </Label>
                          <Input
                            placeholder={rule.condition.type === "keyword" ? "退货, 换货" : "product_search"}
                            value={
                              rule.condition.type === "keyword"
                                ? (rule.condition.keywords || []).join(", ")
                                : (rule.condition.intents || []).join(", ")
                            }
                            onChange={(e) =>
                              handleRuleChange(
                                index,
                                rule.condition.type === "keyword" ? "keywords" : "intents",
                                e.target.value
                              )
                            }
                          />
                        </div>

                        <div className="space-y-1">
                          <Label className="text-xs">目标 Agent</Label>
                          <Select
                            value={rule.target}
                            onValueChange={(v) => handleRuleChange(index, "target", v)}
                          >
                            <SelectTrigger>
                              <SelectValue />
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
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Supervisor 提示词 */}
          <Card>
            <CardHeader>
              <CardTitle>Supervisor 提示词</CardTitle>
              <CardDescription>指导 Supervisor 如何分析用户意图并进行路由</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={supervisorPrompt}
                onChange={(e) => setSupervisorPrompt(e.target.value)}
                rows={10}
                className="font-mono text-sm"
              />
            </CardContent>
          </Card>
        </>
      )}

      {/* 保存按钮 */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "保存中..." : "保存配置"}
        </Button>
      </div>
    </div>
  );
}
