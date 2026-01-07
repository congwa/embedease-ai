"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Slider } from "@/components/ui/slider";
import { Save, Loader2, Globe, Headphones, Code } from "lucide-react";
import { GreetingPreview } from "@/components/admin/greeting";
import { RichEditor } from "@/components/admin/rich-editor";
import {
  getAgentGreeting,
  updateAgentGreeting,
  type GreetingConfig,
  type GreetingChannel,
  type GreetingCTA,
} from "@/lib/api/agents";
import { useAgentDetail } from "@/lib/hooks/use-agents";

const DEFAULT_CONFIG: GreetingConfig = {
  enabled: false,
  trigger: "first_visit",
  delay_ms: 1000,
  channels: {},
  cta: undefined,
  variables: [],
};

const DEFAULT_CHANNEL: GreetingChannel = {
  title: "",
  subtitle: "",
  body: "",
  cta: undefined,
};

const CHANNEL_CONFIG = [
  { id: "web", label: "网页端", icon: Globe, description: "嵌入式 Widget" },
  { id: "support", label: "客服端", icon: Headphones, description: "客服工作台" },
  { id: "api", label: "API", icon: Code, description: "第三方集成" },
];

export default function GreetingConfigPage() {
  const params = useParams();
  const agentId = params.agentId as string;
  const { agent } = useAgentDetail({ agentId });

  const [config, setConfig] = useState<GreetingConfig>(DEFAULT_CONFIG);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activeChannel, setActiveChannel] = useState("web");
  const [hasChanges, setHasChanges] = useState(false);

  // 加载配置
  useEffect(() => {
    const loadConfig = async () => {
      try {
        setIsLoading(true);
        const data = await getAgentGreeting(agentId);
        if (data) {
          setConfig(data);
        }
      } catch (error) {
        console.error("加载开场白配置失败:", error);
      } finally {
        setIsLoading(false);
      }
    };
    loadConfig();
  }, [agentId]);

  // 获取当前渠道配置
  const currentChannel = config.channels[activeChannel] || DEFAULT_CHANNEL;

  // 更新渠道配置
  const updateChannel = useCallback(
    (updates: Partial<GreetingChannel>) => {
      setConfig((prev) => ({
        ...prev,
        channels: {
          ...prev.channels,
          [activeChannel]: {
            ...DEFAULT_CHANNEL,
            ...prev.channels[activeChannel],
            ...updates,
          },
        },
      }));
      setHasChanges(true);
    },
    [activeChannel]
  );

  // 更新顶层配置
  const updateConfig = useCallback((updates: Partial<GreetingConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
    setHasChanges(true);
  }, []);

  // 更新 CTA
  const updateCTA = useCallback(
    (cta: Partial<GreetingCTA> | undefined, isChannel = false) => {
      if (isChannel) {
        updateChannel({ cta: cta as GreetingCTA });
      } else {
        setConfig((prev) => ({
          ...prev,
          cta: cta ? { text: "", payload: "", ...prev.cta, ...cta } : undefined,
        }));
        setHasChanges(true);
      }
    },
    [updateChannel]
  );

  // 保存配置
  const handleSave = async () => {
    try {
      setIsSaving(true);
      await updateAgentGreeting(agentId, config);
      setHasChanges(false);
    } catch (error) {
      console.error("保存开场白配置失败:", error);
      alert("保存失败，请重试");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* 左侧：配置区 */}
      <div className="space-y-6 lg:col-span-2">
        {/* 基础设置 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">基础设置</CardTitle>
            <CardDescription>配置开场白的触发条件和基本参数</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 启用开关 */}
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm font-medium">启用开场白</Label>
                <p className="text-xs text-zinc-500">开启后，用户进入会话时将自动展示开场白</p>
              </div>
              <Switch
                checked={config.enabled}
                onCheckedChange={(checked: boolean) => updateConfig({ enabled: checked })}
              />
            </div>

            {/* 触发策略 */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">触发策略</Label>
              <RadioGroup
                value={config.trigger}
                onValueChange={(value) =>
                  updateConfig({ trigger: value as "first_visit" | "every_session" })
                }
                disabled={!config.enabled}
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="first_visit" id="first_visit" />
                  <Label htmlFor="first_visit" className="font-normal">
                    仅首次访问
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="every_session" id="every_session" />
                  <Label htmlFor="every_session" className="font-normal">
                    每次会话
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* 延迟时间 */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">展示延迟</Label>
                <span className="text-sm text-zinc-500">{config.delay_ms}ms</span>
              </div>
              <Slider
                value={[config.delay_ms]}
                onValueChange={(values: number[]) => updateConfig({ delay_ms: values[0] })}
                min={0}
                max={5000}
                step={100}
                disabled={!config.enabled}
              />
              <p className="text-xs text-zinc-500">
                设置开场白在会话开始后多久展示，0 表示立即展示
              </p>
            </div>

            {/* 默认 CTA */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">默认 CTA 按钮</Label>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <Label className="text-xs text-zinc-500">按钮文本</Label>
                  <Input
                    value={config.cta?.text || ""}
                    onChange={(e) => updateCTA({ text: e.target.value })}
                    placeholder="如：快速提问"
                    disabled={!config.enabled}
                  />
                </div>
                <div>
                  <Label className="text-xs text-zinc-500">触发消息</Label>
                  <Input
                    value={config.cta?.payload || ""}
                    onChange={(e) => updateCTA({ payload: e.target.value })}
                    placeholder="如：推荐热门商品"
                    disabled={!config.enabled}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 渠道配置 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">渠道配置</CardTitle>
            <CardDescription>为不同渠道配置专属的开场白内容</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeChannel} onValueChange={setActiveChannel}>
              <TabsList className="mb-4">
                {CHANNEL_CONFIG.map((ch) => (
                  <TabsTrigger key={ch.id} value={ch.id} className="gap-1.5">
                    <ch.icon className="h-4 w-4" />
                    {ch.label}
                  </TabsTrigger>
                ))}
              </TabsList>

              {CHANNEL_CONFIG.map((ch) => (
                <TabsContent key={ch.id} value={ch.id} className="space-y-4">
                  <p className="text-sm text-zinc-500">{ch.description}</p>

                  {/* 标题 */}
                  <div>
                    <Label className="text-xs text-zinc-500">标题（可选）</Label>
                    <Input
                      value={currentChannel.title || ""}
                      onChange={(e) => updateChannel({ title: e.target.value })}
                      placeholder={`如：您好，我是${agent?.name || "智能助手"}`}
                      disabled={!config.enabled}
                    />
                  </div>

                  {/* 副标题 */}
                  <div>
                    <Label className="text-xs text-zinc-500">副标题（可选）</Label>
                    <Input
                      value={currentChannel.subtitle || ""}
                      onChange={(e) => updateChannel({ subtitle: e.target.value })}
                      placeholder="如：有什么可以帮您的？"
                      disabled={!config.enabled}
                    />
                  </div>

                  {/* 正文内容 */}
                  <div>
                    <Label className="text-xs text-zinc-500">正文内容 *</Label>
                    <RichEditor
                      initialContent={currentChannel.body || ""}
                      onMarkdownChange={(body: string) => updateChannel({ body })}
                      placeholder="输入开场白内容，支持富文本格式..."
                      editable={config.enabled}
                      minHeight={150}
                      showToolbar={true}
                    />
                  </div>

                  {/* 渠道专属 CTA */}
                  <div className="space-y-2">
                    <Label className="text-xs text-zinc-500">渠道专属 CTA（覆盖默认）</Label>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Input
                        value={currentChannel.cta?.text || ""}
                        onChange={(e) =>
                          updateChannel({
                            cta: { text: e.target.value, payload: currentChannel.cta?.payload || "" },
                          })
                        }
                        placeholder="按钮文本"
                        disabled={!config.enabled}
                      />
                      <Input
                        value={currentChannel.cta?.payload || ""}
                        onChange={(e) =>
                          updateChannel({
                            cta: { text: currentChannel.cta?.text || "", payload: e.target.value },
                          })
                        }
                        placeholder="触发消息"
                        disabled={!config.enabled}
                      />
                    </div>
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>

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

      {/* 右侧：预览区 */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-100">实时预览</h3>
        <GreetingPreview
          title={currentChannel.title}
          subtitle={currentChannel.subtitle}
          body={currentChannel.body || "请在左侧编辑开场白内容..."}
          cta={currentChannel.cta || config.cta}
          channel={activeChannel as "web" | "support" | "api"}
        />

        {/* 变量提示 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">可用变量</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">
                  {"{{agent_name}}"}
                </code>
                <span className="text-zinc-500">{agent?.name || "Agent 名称"}</span>
              </div>
              <div className="flex justify-between">
                <code className="rounded bg-zinc-100 px-1 dark:bg-zinc-800">
                  {"{{current_time}}"}
                </code>
                <span className="text-zinc-500">当前时间</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
