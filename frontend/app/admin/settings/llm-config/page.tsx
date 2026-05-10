"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Settings,
  Zap,
  Server,
  Check,
  X,
  Eye,
  EyeOff,
  Loader2,
  AlertCircle,
  RefreshCw,
  ChevronLeft,
  TestTube,
  Save,
} from "lucide-react";
import { PageHeader } from "@/components/admin";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  getSystemConfig,
  getProviderPresets,
  updateQuickConfig,
  updateFullConfig,
  testConfig,
  type SystemConfigMasked,
  type ProviderPreset,
  type QuickConfigUpdate,
  type FullConfigUpdate,
} from "@/lib/api/system-config";

export default function LLMConfigPage() {
  const router = useRouter();
  const [config, setConfig] = useState<SystemConfigMasked | null>(null);
  const [presets, setPresets] = useState<ProviderPreset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<string>("quick");

  // 快速配置表单
  const [quickForm, setQuickForm] = useState<QuickConfigUpdate>({
    api_key: "",
    provider: "siliconflow",
    base_url: "https://api.siliconflow.cn/v1",
  });

  // Base URL 验证错误
  const [baseUrlError, setBaseUrlError] = useState<string | null>(null);

  // 完整配置表单
  const [fullForm, setFullForm] = useState<FullConfigUpdate>({
    llm_provider: "siliconflow",
    llm_api_key: "",
    llm_base_url: "https://api.siliconflow.cn/v1",
    llm_chat_model: "moonshotai/Kimi-K2-Thinking",
    embedding_provider: "siliconflow",
    embedding_api_key: null,
    embedding_base_url: null,
    embedding_model: "Qwen/Qwen3-Embedding-4B",
    embedding_dimension: 2560,
    rerank_enabled: false,
    rerank_provider: null,
    rerank_api_key: null,
    rerank_base_url: null,
    rerank_model: null,
    rerank_top_n: 5,
  });

  // 密码可见性
  const [showApiKey, setShowApiKey] = useState(false);
  const [showFullApiKey, setShowFullApiKey] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [configData, presetsData] = await Promise.all([
        getSystemConfig(),
        getProviderPresets(),
      ]);
      setConfig(configData);
      setPresets(presetsData.items);

      // 如果已有配置，填充表单
      if (configData.initialized) {
        setFullForm({
          llm_provider: configData.llm_provider,
          llm_api_key: "", // 不回显密码
          llm_base_url: configData.llm_base_url,
          llm_chat_model: configData.llm_chat_model,
          embedding_provider: configData.embedding_provider,
          embedding_api_key: null,
          embedding_base_url: configData.embedding_base_url,
          embedding_model: configData.embedding_model,
          embedding_dimension: configData.embedding_dimension,
          rerank_enabled: configData.rerank_enabled,
          rerank_provider: configData.rerank_provider,
          rerank_api_key: null,
          rerank_base_url: configData.rerank_base_url,
          rerank_model: configData.rerank_model,
          rerank_top_n: configData.rerank_top_n,
        });
        setQuickForm({
          api_key: "",
          provider: configData.llm_provider,
          base_url: configData.llm_base_url,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 验证 Base URL
  const validateBaseUrl = (url: string): string | null => {
    if (!url) {
      return "Base URL 不能为空";
    }
    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        return "URL 必须以 http:// 或 https:// 开头";
      }
      return null;
    } catch {
      return "请输入有效的 URL 格式";
    }
  };

  // 切换提供商时更新默认值
  const handleProviderChange = (provider: string) => {
    const preset = presets.find((p) => p.id === provider);
    if (preset) {
      setQuickForm((prev) => ({ ...prev, provider, base_url: preset.base_url }));
      setBaseUrlError(null);
      setFullForm((prev) => ({
        ...prev,
        llm_provider: provider,
        llm_base_url: preset.base_url,
        llm_chat_model: preset.default_model,
        embedding_provider: provider,
        embedding_model: preset.default_embedding_model || prev.embedding_model,
        embedding_dimension: preset.default_embedding_dimension || prev.embedding_dimension,
      }));
    }
  };

  // 测试配置
  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);

    try {
      const apiKey = activeTab === "quick" ? quickForm.api_key : fullForm.llm_api_key;
      const provider = activeTab === "quick" ? quickForm.provider || "siliconflow" : fullForm.llm_provider;
      const baseUrl = activeTab === "quick" 
        ? quickForm.base_url || "https://api.siliconflow.cn/v1"
        : fullForm.llm_base_url;

      const result = await testConfig({
        provider,
        api_key: apiKey,
        base_url: baseUrl,
      });
      setTestResult(result);
    } catch (e) {
      setTestResult({
        success: false,
        message: e instanceof Error ? e.message : "测试失败",
      });
    } finally {
      setIsTesting(false);
    }
  };

  // 保存快速配置
  const handleQuickSave = async () => {
    if (!quickForm.api_key) {
      setError("请输入 API Key");
      return;
    }

    if (!quickForm.base_url) {
      setError("请输入 Base URL");
      return;
    }

    const urlError = validateBaseUrl(quickForm.base_url);
    if (urlError) {
      setBaseUrlError(urlError);
      setError(urlError);
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const result = await updateQuickConfig(quickForm);
      setConfig(result);
      setTestResult({ success: true, message: "配置已保存" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  // 保存完整配置
  const handleFullSave = async () => {
    if (!fullForm.llm_api_key) {
      setError("请输入 LLM API Key");
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const result = await updateFullConfig(fullForm);
      setConfig(result);
      setTestResult({ success: true, message: "配置已保存" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/admin/settings")}>
            <ChevronLeft className="h-5 w-5" />
          </Button>
          <PageHeader
            title="LLM 配置"
            description="配置大语言模型、Embedding 和 Rerank 服务"
          />
        </div>
        <Button variant="outline" size="sm" onClick={loadData}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {/* 当前状态 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Server className="h-4 w-4" />
            当前配置状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border p-3">
              <div className="text-xs text-zinc-500">配置状态</div>
              <div className="mt-1 flex items-center gap-2">
                {config?.initialized ? (
                  <>
                    <Badge variant="default" className="bg-green-100 text-green-700">
                      <Check className="mr-1 h-3 w-3" />
                      已配置
                    </Badge>
                  </>
                ) : (
                  <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                    <AlertCircle className="mr-1 h-3 w-3" />
                    未配置
                  </Badge>
                )}
              </div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-zinc-500">配置来源</div>
              <div className="mt-1 font-medium">
                {config?.source === "database" ? "后台配置" : "环境变量"}
              </div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-zinc-500">LLM 提供商</div>
              <div className="mt-1 font-medium">{config?.llm_provider || "-"}</div>
            </div>
            <div className="rounded-lg border p-3">
              <div className="text-xs text-zinc-500">API Key</div>
              <div className="mt-1 font-mono text-sm">{config?.llm_api_key_masked || "-"}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 错误提示 */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-red-600 dark:bg-red-900/20 dark:text-red-400 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* 测试结果 */}
      {testResult && (
        <div
          className={cn(
            "rounded-lg p-4 flex items-center gap-2",
            testResult.success
              ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
              : "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400"
          )}
        >
          {testResult.success ? (
            <Check className="h-5 w-5 flex-shrink-0" />
          ) : (
            <X className="h-5 w-5 flex-shrink-0" />
          )}
          {testResult.message}
        </div>
      )}

      {/* 配置表单 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">配置 LLM 服务</CardTitle>
          <CardDescription>
            选择快速配置（推荐新手）或完整配置（高级用户）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2 lg:w-[400px]">
              <TabsTrigger value="quick" className="gap-2">
                <Zap className="h-4 w-4" />
                快速配置
              </TabsTrigger>
              <TabsTrigger value="full" className="gap-2">
                <Settings className="h-4 w-4" />
                完整配置
              </TabsTrigger>
            </TabsList>

            {/* 快速配置 */}
            <TabsContent value="quick" className="mt-6 space-y-6">
              <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-4 text-sm text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-300">
                <strong>快速配置</strong>：选择提供商，填写 API Key 和 Base URL，然后测试连接。
              </div>

              <div className="space-y-4">
                {/* 提供商选择 */}
                <div className="space-y-2">
                  <Label htmlFor="quick-provider">选择提供商</Label>
                  <Select
                    value={quickForm.provider}
                    onValueChange={(value) => handleProviderChange(value)}
                  >
                    <SelectTrigger id="quick-provider" className="w-full md:w-[300px]">
                      <SelectValue placeholder="选择提供商" />
                    </SelectTrigger>
                    <SelectContent>
                      {presets.map((preset) => (
                        <SelectItem key={preset.id} value={preset.id}>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{preset.name}</span>
                            <span className="text-xs text-zinc-400">({preset.id})</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-zinc-500">
                    选择提供商后会自动填充默认的 Base URL，你也可以手动修改
                  </p>
                </div>

                {/* Base URL 输入 */}
                <div className="space-y-2">
                  <Label htmlFor="quick-base-url">Base URL</Label>
                  <Input
                    id="quick-base-url"
                    type="url"
                    placeholder="https://api.example.com/v1"
                    value={quickForm.base_url || ""}
                    onChange={(e) => {
                      const value = e.target.value;
                      setQuickForm((prev) => ({ ...prev, base_url: value }));
                      setBaseUrlError(validateBaseUrl(value));
                    }}
                    className={cn(
                      "w-full md:w-[500px]",
                      baseUrlError && "border-red-500 focus-visible:ring-red-500"
                    )}
                  />
                  {baseUrlError ? (
                    <p className="text-xs text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      {baseUrlError}
                    </p>
                  ) : (
                    <p className="text-xs text-zinc-500">
                      API 服务的基础 URL，通常以 /v1 结尾
                    </p>
                  )}
                </div>

                {/* API Key 输入 */}
                <div className="space-y-2">
                  <Label htmlFor="quick-api-key">API Key</Label>
                  <div className="relative w-full md:w-[500px]">
                    <Input
                      id="quick-api-key"
                      type={showApiKey ? "text" : "password"}
                      placeholder="sk-..."
                      value={quickForm.api_key}
                      onChange={(e) =>
                        setQuickForm((prev) => ({ ...prev, api_key: e.target.value }))
                      }
                      className="pr-10"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                      onClick={() => setShowApiKey(!showApiKey)}
                    >
                      {showApiKey ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-zinc-500">
                    从提供商控制台获取的 API 密钥
                  </p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={!quickForm.api_key || !quickForm.base_url || !!baseUrlError || isTesting}
                >
                  {isTesting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <TestTube className="mr-2 h-4 w-4" />
                  )}
                  测试连接
                </Button>
                <Button
                  onClick={handleQuickSave}
                  disabled={!quickForm.api_key || !quickForm.base_url || !!baseUrlError || isSaving}
                >
                  {isSaving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  保存配置
                </Button>
              </div>
            </TabsContent>

            {/* 完整配置 */}
            <TabsContent value="full" className="mt-6 space-y-6">
              {/* LLM 配置 */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  LLM 配置
                </h3>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="full-provider">提供商</Label>
                    <Select
                      value={fullForm.llm_provider}
                      onValueChange={(value) => handleProviderChange(value)}
                    >
                      <SelectTrigger id="full-provider">
                        <SelectValue placeholder="选择提供商" />
                      </SelectTrigger>
                      <SelectContent>
                        {presets.map((preset) => (
                          <SelectItem key={preset.id} value={preset.id}>
                            {preset.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="full-api-key">API Key</Label>
                    <div className="relative">
                      <Input
                        id="full-api-key"
                        type={showFullApiKey ? "text" : "password"}
                        placeholder="sk-..."
                        value={fullForm.llm_api_key}
                        onChange={(e) =>
                          setFullForm((prev) => ({ ...prev, llm_api_key: e.target.value }))
                        }
                        className="pr-10"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                        onClick={() => setShowFullApiKey(!showFullApiKey)}
                      >
                        {showFullApiKey ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="full-base-url">Base URL</Label>
                    <Input
                      id="full-base-url"
                      placeholder="https://api.example.com/v1"
                      value={fullForm.llm_base_url}
                      onChange={(e) =>
                        setFullForm((prev) => ({ ...prev, llm_base_url: e.target.value }))
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="full-model">聊天模型</Label>
                    <Input
                      id="full-model"
                      placeholder="模型 ID"
                      value={fullForm.llm_chat_model}
                      onChange={(e) =>
                        setFullForm((prev) => ({ ...prev, llm_chat_model: e.target.value }))
                      }
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* Embedding 配置 */}
              <div className="space-y-4">
                <h3 className="text-sm font-medium flex items-center gap-2">
                  <Settings className="h-4 w-4" />
                  Embedding 配置
                </h3>
                <p className="text-xs text-zinc-500">
                  留空 API Key 和 Base URL 将使用 LLM 的配置
                </p>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="embedding-model">Embedding 模型</Label>
                    <Input
                      id="embedding-model"
                      placeholder="text-embedding-3-large"
                      value={fullForm.embedding_model}
                      onChange={(e) =>
                        setFullForm((prev) => ({ ...prev, embedding_model: e.target.value }))
                      }
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="embedding-dimension">向量维度</Label>
                    <Input
                      id="embedding-dimension"
                      type="number"
                      placeholder="2560"
                      value={fullForm.embedding_dimension}
                      onChange={(e) =>
                        setFullForm((prev) => ({
                          ...prev,
                          embedding_dimension: parseInt(e.target.value) || 2560,
                        }))
                      }
                    />
                  </div>
                </div>
              </div>

              <Separator />

              {/* Rerank 配置 */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium flex items-center gap-2">
                    <Settings className="h-4 w-4" />
                    Rerank 配置
                  </h3>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="rerank-enabled" className="text-sm">
                      启用 Rerank
                    </Label>
                    <Switch
                      id="rerank-enabled"
                      checked={fullForm.rerank_enabled}
                      onCheckedChange={(checked) =>
                        setFullForm((prev) => ({ ...prev, rerank_enabled: checked }))
                      }
                    />
                  </div>
                </div>

                {fullForm.rerank_enabled && (
                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="rerank-model">Rerank 模型</Label>
                      <Input
                        id="rerank-model"
                        placeholder="Qwen/Qwen3-Reranker-8B"
                        value={fullForm.rerank_model || ""}
                        onChange={(e) =>
                          setFullForm((prev) => ({ ...prev, rerank_model: e.target.value }))
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="rerank-top-n">Top N</Label>
                      <Input
                        id="rerank-top-n"
                        type="number"
                        placeholder="5"
                        value={fullForm.rerank_top_n}
                        onChange={(e) =>
                          setFullForm((prev) => ({
                            ...prev,
                            rerank_top_n: parseInt(e.target.value) || 5,
                          }))
                        }
                      />
                    </div>
                  </div>
                )}
              </div>

              <Separator />

              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={handleTest}
                  disabled={!fullForm.llm_api_key || isTesting}
                >
                  {isTesting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <TestTube className="mr-2 h-4 w-4" />
                  )}
                  测试连接
                </Button>
                <Button
                  onClick={handleFullSave}
                  disabled={!fullForm.llm_api_key || isSaving}
                >
                  {isSaving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  保存配置
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
