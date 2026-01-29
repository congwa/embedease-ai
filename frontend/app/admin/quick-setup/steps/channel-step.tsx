"use client";

import { useState } from "react";
import {
  Globe,
  Headphones,
  Webhook,
  MessageSquare,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import type { StepProps } from "@/types/quick-setup";

export function ChannelStep({ step, onComplete, onSkip, isLoading }: StepProps) {
  const [formData, setFormData] = useState({
    web_enabled: (step.data?.web_enabled as boolean) ?? true,
    support_enabled: (step.data?.support_enabled as boolean) ?? false,
    webhook_url: (step.data?.webhook_url as string) || "",
  });

  const handleSubmit = () => {
    onComplete(formData);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">渠道 & 集成</h2>
        <p className="text-zinc-500">
          配置客服入口和第三方集成，扩展 Agent 的触达渠道。
        </p>
      </div>

      {/* Web 渠道 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Globe className="h-4 w-4" />
              网页嵌入
            </span>
            <Switch
              checked={formData.web_enabled}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, web_enabled: checked })
              }
            />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-500">
            通过 JavaScript SDK 将 Agent 嵌入到您的网站中。
          </p>
          {formData.web_enabled && (
            <div className="mt-4 rounded-lg bg-zinc-100 p-4 dark:bg-zinc-800">
              <code className="text-xs">
                {'<script src="/embed/widget.js"></script>'}
              </code>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Support 渠道 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Headphones className="h-4 w-4" />
              客服控制台
            </span>
            <Switch
              checked={formData.support_enabled}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, support_enabled: checked })
              }
            />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-500">
            启用后，客服人员可通过控制台接管对话。
          </p>
          {formData.support_enabled && (
            <div className="mt-4 text-sm">
              <p>
                控制台入口：
                <code className="ml-2 bg-zinc-100 px-2 py-1 rounded dark:bg-zinc-800">
                  /admin/support
                </code>
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Webhook */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Webhook className="h-4 w-4" />
            Webhook 通知
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-zinc-500">
            配置 Webhook URL，当有新消息时会发送 HTTP POST 通知。
          </p>
          <div className="space-y-2">
            <Label>Webhook URL</Label>
            <Input
              placeholder="https://your-server.com/webhook"
              value={formData.webhook_url}
              onChange={(e) =>
                setFormData({ ...formData, webhook_url: e.target.value })
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* 暂不支持的集成 */}
      <Card className="border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base text-zinc-400">
            <MessageSquare className="h-4 w-4" />
            更多集成
            <Badge variant="outline" className="text-zinc-400">
              即将推出
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-zinc-400">
              <AlertTriangle className="h-5 w-5" />
              <div>
                <div className="font-medium">企业微信</div>
                <div className="text-xs">通过 .env 配置 WEWORK_* 参数</div>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-zinc-400">
              <AlertTriangle className="h-5 w-5" />
              <div>
                <div className="font-medium">Slack</div>
                <div className="text-xs">暂不支持</div>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-zinc-400">
              <AlertTriangle className="h-5 w-5" />
              <div>
                <div className="font-medium">钉钉</div>
                <div className="text-xs">暂不支持</div>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-dashed p-4 text-zinc-400">
              <AlertTriangle className="h-5 w-5" />
              <div>
                <div className="font-medium">CRM 集成</div>
                <div className="text-xs">暂不支持</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => onSkip()} disabled={isLoading}>
          跳过此步
        </Button>
        <Button onClick={handleSubmit} disabled={isLoading}>
          保存并继续
        </Button>
      </div>
    </div>
  );
}
