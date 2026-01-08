"use client";

import { useState } from "react";
import { Building, Globe, Clock, Mail } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { type StepProps } from "../page";

export function SystemStep({ step, onComplete, onSkip, isLoading }: StepProps) {
  const [formData, setFormData] = useState({
    company_name: (step.data?.company_name as string) || "",
    brand_theme: (step.data?.brand_theme as string) || "default",
    language: (step.data?.language as string) || "zh-CN",
    timezone: (step.data?.timezone as string) || "Asia/Shanghai",
    admin_contact: (step.data?.admin_contact as string) || "",
  });

  const handleSubmit = () => {
    onComplete(formData);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-2">系统基础设置</h2>
        <p className="text-zinc-500">
          配置公司信息和基础偏好设置，这些信息将用于 Agent 的上下文中。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Building className="h-4 w-4" />
            公司信息
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="company_name">公司/品牌名称</Label>
              <Input
                id="company_name"
                placeholder="例如：XX科技"
                value={formData.company_name}
                onChange={(e) =>
                  setFormData({ ...formData, company_name: e.target.value })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="brand_theme">品牌主题</Label>
              <Select
                value={formData.brand_theme}
                onValueChange={(value) =>
                  setFormData({ ...formData, brand_theme: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择主题" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="default">默认</SelectItem>
                  <SelectItem value="professional">专业</SelectItem>
                  <SelectItem value="friendly">亲和</SelectItem>
                  <SelectItem value="tech">科技</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4" />
            区域设置
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="language">
                <Globe className="inline h-3 w-3 mr-1" />
                语言
              </Label>
              <Select
                value={formData.language}
                onValueChange={(value) =>
                  setFormData({ ...formData, language: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择语言" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="zh-CN">简体中文</SelectItem>
                  <SelectItem value="zh-TW">繁體中文</SelectItem>
                  <SelectItem value="en-US">English (US)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">
                <Clock className="inline h-3 w-3 mr-1" />
                时区
              </Label>
              <Select
                value={formData.timezone}
                onValueChange={(value) =>
                  setFormData({ ...formData, timezone: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择时区" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Asia/Shanghai">
                    中国标准时间 (UTC+8)
                  </SelectItem>
                  <SelectItem value="Asia/Hong_Kong">香港时间 (UTC+8)</SelectItem>
                  <SelectItem value="Asia/Tokyo">日本时间 (UTC+9)</SelectItem>
                  <SelectItem value="America/New_York">
                    美东时间 (UTC-5)
                  </SelectItem>
                  <SelectItem value="Europe/London">伦敦时间 (UTC+0)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Mail className="h-4 w-4" />
            联系方式
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Label htmlFor="admin_contact">管理员联系方式</Label>
            <Input
              id="admin_contact"
              placeholder="例如：admin@example.com 或 客服热线"
              value={formData.admin_contact}
              onChange={(e) =>
                setFormData({ ...formData, admin_contact: e.target.value })
              }
            />
            <p className="text-xs text-zinc-500">
              当用户请求人工服务时，可展示此联系方式
            </p>
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
