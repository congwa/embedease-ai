"use client";

import { useEffect, useState } from "react";
import { Network, Bot, AlertCircle, CheckCircle2, XCircle, Clock, Save, Loader2, Plus, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/admin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { 
  getSupervisorGlobalConfig, 
  updateSupervisorGlobalConfig,
  getAvailableAgentsForSupervisor,
  type SupervisorGlobalConfig,
  type SupervisorSubAgent,
  type AvailableAgentForSupervisor,
} from "@/lib/api/admin";

const DEFAULT_SUPERVISOR_PROMPT = `你是一个智能助手调度器（Supervisor）。

你的职责是分析用户的问题，并将其路由到最合适的专业助手处理。

## 可用助手
{agent_descriptions}

## 路由规则
1. 分析用户意图，选择最匹配的助手
2. 如果问题涉及多个领域，选择主要相关的助手
3. 如果无法确定，使用默认助手

## 输出格式
直接调用 transfer_to_xxx 工具将对话转交给对应助手。`;

export default function SupervisorSettingsPage() {
  const [config, setConfig] = useState<SupervisorGlobalConfig | null>(null);
  const [availableAgents, setAvailableAgents] = useState<AvailableAgentForSupervisor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  
  // 编辑状态
  const [enabled, setEnabled] = useState(false);
  const [supervisorPrompt, setSupervisorPrompt] = useState("");
  const [subAgents, setSubAgents] = useState<SupervisorSubAgent[]>([]);
  const [routingType, setRoutingType] = useState("hybrid");
  const [defaultAgentId, setDefaultAgentId] = useState<string | null>(null);
  const [intentTimeout, setIntentTimeout] = useState(3.0);
  const [allowMultiAgent, setAllowMultiAgent] = useState(false);

  useEffect(() => {
    async function loadConfig() {
      try {
        setIsLoading(true);
        const [globalConfig, agents] = await Promise.all([
          getSupervisorGlobalConfig(),
          getAvailableAgentsForSupervisor(),
        ]);
        setConfig(globalConfig);
        setAvailableAgents(agents);
        
        // 初始化编辑状态
        setEnabled(globalConfig.enabled);
        setSupervisorPrompt(globalConfig.supervisor_prompt || "");
        setSubAgents(globalConfig.sub_agents);
        setRoutingType(globalConfig.routing_policy.type);
        setDefaultAgentId(globalConfig.routing_policy.default_agent_id);
        setIntentTimeout(globalConfig.intent_timeout);
        setAllowMultiAgent(globalConfig.allow_multi_agent);
      } catch (e) {
        setError(e instanceof Error ? e.message : "加载失败");
      } finally {
        setIsLoading(false);
      }
    }
    loadConfig();
  }, []);
  
  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    try {
      const result = await updateSupervisorGlobalConfig({
        enabled,
        supervisor_prompt: supervisorPrompt || null,
        sub_agents: subAgents,
        routing_policy: {
          type: routingType,
          rules: config?.routing_policy.rules || [],
          default_agent_id: defaultAgentId,
        },
        intent_timeout: intentTimeout,
        allow_multi_agent: allowMultiAgent,
      });
      setConfig(result);
      setSaveStatus({ type: "success", message: "配置已保存，立即生效" });
    } catch (e) {
      setSaveStatus({ type: "error", message: e instanceof Error ? e.message : "保存失败" });
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleAddSubAgent = (agent: AvailableAgentForSupervisor) => {
    const newSubAgent: SupervisorSubAgent = {
      agent_id: agent.id,
      name: agent.name,
      description: agent.description,
      routing_hints: [],
      priority: subAgents.length > 0 ? Math.max(...subAgents.map(s => s.priority)) - 10 : 100,
    };
    setSubAgents([...subAgents, newSubAgent]);
    setShowAddDialog(false);
  };
  
  const handleRemoveSubAgent = (agentId: string) => {
    setSubAgents(subAgents.filter(s => s.agent_id !== agentId));
  };
  
  const handleSubAgentChange = (agentId: string, field: keyof SupervisorSubAgent, value: unknown) => {
    setSubAgents(subAgents.map(s => 
      s.agent_id === agentId ? { ...s, [field]: value } : s
    ));
  };
  
  const hasChanges = config && (
    enabled !== config.enabled ||
    supervisorPrompt !== (config.supervisor_prompt || "") ||
    JSON.stringify(subAgents) !== JSON.stringify(config.sub_agents) ||
    routingType !== config.routing_policy.type ||
    defaultAgentId !== config.routing_policy.default_agent_id ||
    intentTimeout !== config.intent_timeout ||
    allowMultiAgent !== config.allow_multi_agent
  );
  
  const unselectedAgents = availableAgents.filter(
    a => !subAgents.some(s => s.agent_id === a.id)
  );

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-600 dark:bg-red-900/20 dark:text-red-400">
        {error}
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Supervisor 配置"
        description="多 Agent 编排全局配置"
      />

      {/* 保存状态提示 */}
      {saveStatus && (
        <Alert variant={saveStatus.type === "success" ? "default" : "destructive"}>
          {saveStatus.type === "success" ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <AlertDescription>{saveStatus.message}</AlertDescription>
        </Alert>
      )}

      {/* 全局开关 */}
      <Card className={enabled ? "border-green-200 bg-green-50/30 dark:border-green-900 dark:bg-green-950/20" : "border-zinc-200 dark:border-zinc-800"}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${enabled ? "bg-green-500/10" : "bg-zinc-500/10"}`}>
                {enabled ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : (
                  <XCircle className="h-5 w-5 text-zinc-400" />
                )}
              </div>
              <div>
                <CardTitle className="text-lg">Supervisor 全局开关</CardTitle>
                <CardDescription>
                  {enabled ? "已启用，Agent 可使用多 Agent 编排功能" : "已禁用，所有 Supervisor Agent 将回退到单 Agent 模式"}
                </CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch
                checked={enabled}
                onCheckedChange={setEnabled}
              />
              <Badge variant={enabled ? "default" : "secondary"} className="text-sm">
                {enabled ? "已启用" : "已禁用"}
              </Badge>
            </div>
          </div>
        </CardHeader>
        {config?.source === "env" && (
          <CardContent>
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                当前配置来源：环境变量。保存后将使用数据库配置，无需重启服务。
              </AlertDescription>
            </Alert>
          </CardContent>
        )}
      </Card>

      {/* 调度器提示词 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-4 w-4" />
            调度器提示词
          </CardTitle>
          <CardDescription>
            指导 Supervisor 如何分析用户意图和路由请求
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            value={supervisorPrompt}
            onChange={(e) => setSupervisorPrompt(e.target.value)}
            placeholder={DEFAULT_SUPERVISOR_PROMPT}
            className="min-h-[200px] font-mono text-sm"
          />
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSupervisorPrompt(DEFAULT_SUPERVISOR_PROMPT)}
            >
              重置为默认
            </Button>
            <span className="text-xs text-zinc-500">
              提示：使用 {"{agent_descriptions}"} 占位符插入子 Agent 描述
            </span>
          </div>
        </CardContent>
      </Card>

      {/* 子 Agent 管理 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-orange-500" />
              <CardTitle className="text-base">子 Agent 管理</CardTitle>
              <Badge variant="outline">{subAgents.length} 个</Badge>
            </div>
            <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
              <DialogTrigger asChild>
                <Button size="sm" disabled={unselectedAgents.length === 0}>
                  <Plus className="mr-1 h-4 w-4" />
                  添加子 Agent
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>选择子 Agent</DialogTitle>
                  <DialogDescription>
                    选择要加入 Supervisor 编排的 Agent
                  </DialogDescription>
                </DialogHeader>
                <div className="max-h-[300px] space-y-2 overflow-y-auto">
                  {unselectedAgents.map((agent) => (
                    <div
                      key={agent.id}
                      className="flex cursor-pointer items-center justify-between rounded-lg border p-3 hover:bg-zinc-50 dark:hover:bg-zinc-900"
                      onClick={() => handleAddSubAgent(agent)}
                    >
                      <div>
                        <p className="font-medium">{agent.name}</p>
                        <p className="text-xs text-zinc-500">{agent.type}</p>
                      </div>
                      <Plus className="h-4 w-4 text-zinc-400" />
                    </div>
                  ))}
                  {unselectedAgents.length === 0 && (
                    <p className="py-4 text-center text-sm text-zinc-500">
                      没有可添加的 Agent
                    </p>
                  )}
                </div>
              </DialogContent>
            </Dialog>
          </div>
          <CardDescription>
            配置参与多 Agent 编排的子 Agent
          </CardDescription>
        </CardHeader>
        <CardContent>
          {subAgents.length === 0 ? (
            <div className="py-8 text-center">
              <Network className="mx-auto h-12 w-12 text-zinc-300 dark:text-zinc-600" />
              <p className="mt-4 text-sm text-zinc-500">暂无子 Agent</p>
              <p className="mt-1 text-xs text-zinc-400">
                点击上方按钮添加子 Agent
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {subAgents.map((agent) => (
                <div
                  key={agent.agent_id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                      <Bot className="h-5 w-5 text-blue-500" />
                    </div>
                    <div className="space-y-1">
                      <p className="font-medium">{agent.name}</p>
                      <Input
                        placeholder="路由关键词（逗号分隔）"
                        value={agent.routing_hints.join(", ")}
                        onChange={(e) => handleSubAgentChange(
                          agent.agent_id,
                          "routing_hints",
                          e.target.value.split(",").map(s => s.trim()).filter(Boolean)
                        )}
                        className="h-8 w-64 text-xs"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Label className="text-xs">优先级</Label>
                      <Input
                        type="number"
                        min={0}
                        max={1000}
                        value={agent.priority}
                        onChange={(e) => handleSubAgentChange(
                          agent.agent_id,
                          "priority",
                          parseInt(e.target.value) || 0
                        )}
                        className="h-8 w-20"
                      />
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveSubAgent(agent.agent_id)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 配置参数 */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" />
              路由策略
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>策略类型</Label>
              <Select value={routingType} onValueChange={setRoutingType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hybrid">混合模式（推荐）</SelectItem>
                  <SelectItem value="keyword">关键词匹配</SelectItem>
                  <SelectItem value="intent">意图识别</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>默认 Agent</Label>
              <Select
                value={defaultAgentId || "none"}
                onValueChange={(v) => setDefaultAgentId(v === "none" ? null : v)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择默认 Agent" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">不设置</SelectItem>
                  {subAgents.map((agent) => (
                    <SelectItem key={agent.agent_id} value={agent.agent_id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock className="h-4 w-4" />
              高级配置
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="intent-timeout">意图分类超时（秒）</Label>
              <Input
                id="intent-timeout"
                type="number"
                min={0.5}
                max={30}
                step={0.5}
                value={intentTimeout}
                onChange={(e) => setIntentTimeout(parseFloat(e.target.value) || 3.0)}
                className="w-32"
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>多 Agent 协作</Label>
                <p className="text-xs text-zinc-500">允许同时调用多个子 Agent</p>
              </div>
              <Switch
                checked={allowMultiAgent}
                onCheckedChange={setAllowMultiAgent}
              />
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* 保存按钮 */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving || !hasChanges}>
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              保存配置
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
