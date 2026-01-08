"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  MessageSquare,
  Loader2,
  ExternalLink,
  Plus,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type StepProps } from "../page";
import {
  getAgentGreeting,
  updateAgentGreeting,
  type GreetingConfig,
} from "@/lib/api/agents";

const CHANNEL_LABELS: Record<string, string> = {
  default: "默认",
  web: "网页端",
  support: "客服端",
  api: "API",
};

export function GreetingStep({
  state,
  agentTypes,
  onComplete,
  onSkip,
  isLoading,
}: StepProps) {
  const [greetingConfig, setGreetingConfig] = useState<GreetingConfig | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newChannel, setNewChannel] = useState("");

  const agentId = state.agent_id;

  useEffect(() => {
    const load = async () => {
      if (!agentId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const config = await getAgentGreeting(agentId);
        if (config) {
          setGreetingConfig(config);
        } else {
          // 使用类型默认模板
          const agentType = state.steps[3]?.data?.agent_type as string;
          const typeConfig = agentTypes.find((t) => t.type === agentType);
          if (typeConfig?.greeting_template) {
            const template = typeConfig.greeting_template as unknown as GreetingConfig;
            setGreetingConfig(template);
          } else {
            setGreetingConfig({
              enabled: false,
              trigger: "first_visit",
              delay_ms: 1000,
              channels: {},
            });
          }
        }
      } catch (e) {
        console.error("加载开场白配置失败", e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [agentId, agentTypes, state.steps]);

  const handleSave = async () => {
    if (!agentId || !greetingConfig) return;

    try {
      setSaving(true);
      await updateAgentGreeting(agentId, greetingConfig);
      onComplete({ greeting_config: greetingConfig });
    } catch (e) {
      console.error("保存开场白配置失败", e);
    } finally {
      setSaving(false);
    }
  };

  const handleAddChannel = () => {
    if (!newChannel || !greetingConfig) return;
    setGreetingConfig({
      ...greetingConfig,
      channels: {
        ...greetingConfig.channels,
        [newChannel]: {
          body: "欢迎使用！",
        },
      },
    });
    setNewChannel("");
  };

  const handleRemoveChannel = (channelKey: string) => {
    if (!greetingConfig) return;
    const newChannels = { ...greetingConfig.channels };
    delete newChannels[channelKey];
    setGreetingConfig({
      ...greetingConfig,
      channels: newChannels,
    });
  };

  const handleUpdateChannel = (
    channelKey: string,
    field: string,
    value: string
  ) => {
    if (!greetingConfig) return;
    setGreetingConfig({
      ...greetingConfig,
      channels: {
        ...greetingConfig.channels,
        [channelKey]: {
          ...greetingConfig.channels[channelKey],
          [field]: value,
        },
      },
    });
  };

  if (!agentId) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">开场白配置</h2>
          <p className="text-zinc-500">请先在上一步选择要配置的 Agent。</p>
        </div>
        <Button variant="outline" onClick={() => onSkip()}>
          跳过此步
        </Button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">开场白配置</h2>
        <p className="text-zinc-500">
          配置 Agent 的欢迎消息，可针对不同渠道设置不同内容。
        </p>
      </div>

      {/* 基础设置 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              基础设置
            </span>
            <div className="flex items-center gap-2">
              <Label htmlFor="greeting-enabled" className="text-sm font-normal">
                启用开场白
              </Label>
              <Switch
                id="greeting-enabled"
                checked={greetingConfig?.enabled || false}
                onCheckedChange={(checked) =>
                  setGreetingConfig((prev) =>
                    prev ? { ...prev, enabled: checked } : prev
                  )
                }
              />
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>触发策略</Label>
              <Select
                value={greetingConfig?.trigger || "first_visit"}
                onValueChange={(value) =>
                  setGreetingConfig((prev) =>
                    prev
                      ? { ...prev, trigger: value as "first_visit" | "every_session" }
                      : prev
                  )
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="first_visit">首次访问</SelectItem>
                  <SelectItem value="every_session">每次会话</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>展示延迟 (毫秒)</Label>
              <Input
                type="number"
                value={greetingConfig?.delay_ms || 1000}
                onChange={(e) =>
                  setGreetingConfig((prev) =>
                    prev
                      ? { ...prev, delay_ms: parseInt(e.target.value) || 1000 }
                      : prev
                  )
                }
                min={0}
                max={10000}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 渠道配置 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span>渠道配置</span>
            <div className="flex items-center gap-2">
              <Select value={newChannel} onValueChange={setNewChannel}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="添加渠道" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CHANNEL_LABELS)
                    .filter(
                      ([key]) => !greetingConfig?.channels[key]
                    )
                    .map(([key, label]) => (
                      <SelectItem key={key} value={key}>
                        {label}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddChannel}
                disabled={!newChannel}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.keys(greetingConfig?.channels || {}).length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              <p>暂无渠道配置</p>
              <p className="text-sm">请添加至少一个渠道以启用开场白</p>
            </div>
          ) : (
            Object.entries(greetingConfig?.channels || {}).map(
              ([channelKey, channel]) => (
                <div
                  key={channelKey}
                  className="rounded-lg border p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <Badge variant="outline">
                      {CHANNEL_LABELS[channelKey] || channelKey}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveChannel(channelKey)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <Label>标题</Label>
                    <Input
                      placeholder="可选，如：👋 欢迎"
                      value={channel.title || ""}
                      onChange={(e) =>
                        handleUpdateChannel(channelKey, "title", e.target.value)
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>正文内容</Label>
                    <Textarea
                      placeholder="支持 Markdown 格式"
                      value={channel.body || ""}
                      onChange={(e) =>
                        handleUpdateChannel(channelKey, "body", e.target.value)
                      }
                      rows={3}
                    />
                  </div>
                </div>
              )
            )
          )}
        </CardContent>
      </Card>

      {/* CTA 配置 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">快捷操作按钮 (CTA)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>按钮文本</Label>
              <Input
                placeholder="例如：开始购物"
                value={greetingConfig?.cta?.text || ""}
                onChange={(e) =>
                  setGreetingConfig((prev) =>
                    prev
                      ? {
                          ...prev,
                          cta: { ...prev.cta, text: e.target.value, payload: prev.cta?.payload || "" },
                        }
                      : prev
                  )
                }
              />
            </div>
            <div className="space-y-2">
              <Label>触发消息</Label>
              <Input
                placeholder="点击后发送的消息"
                value={greetingConfig?.cta?.payload || ""}
                onChange={(e) =>
                  setGreetingConfig((prev) =>
                    prev
                      ? {
                          ...prev,
                          cta: { ...prev.cta, payload: e.target.value, text: prev.cta?.text || "" },
                        }
                      : prev
                  )
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 快捷入口 */}
      <div className="flex items-center gap-2 text-sm text-zinc-500">
        <span>需要更多配置？</span>
        <Button variant="link" size="sm" className="h-auto p-0" asChild>
          <Link href={`/admin/agents/${agentId}/greeting`}>
            前往完整开场白设置
            <ExternalLink className="ml-1 h-3 w-3" />
          </Link>
        </Button>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => onSkip()} disabled={isLoading}>
          跳过此步
        </Button>
        <Button
          onClick={handleSave}
          disabled={
            isLoading ||
            saving ||
            (greetingConfig?.enabled &&
              Object.keys(greetingConfig?.channels || {}).length === 0)
          }
        >
          {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          保存并继续
        </Button>
      </div>
    </div>
  );
}
