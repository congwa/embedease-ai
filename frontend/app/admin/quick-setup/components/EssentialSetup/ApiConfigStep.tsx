"use client";

import { useState, useEffect } from "react";
import { Eye, EyeOff, CheckCircle, XCircle, Loader2, Sparkles, Zap, ChevronsUpDown, Check } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import {
  getProviders,
  getProviderModels,
  type LLMProvider,
  type LLMModel,
} from "@/lib/api/quick-setup";

interface ApiConfigStepProps {
  provider: string;
  apiKey: string;
  model: string;
  baseUrl?: string;
  // Embedding 独立配置
  embeddingModel: string;
  embeddingDimension: number;
  embeddingApiKey?: string;
  embeddingBaseUrl?: string;
  useSameLlmConfig: boolean;
  onProviderChange: (provider: string) => void;
  onApiKeyChange: (apiKey: string) => void;
  onModelChange: (model: string) => void;
  onBaseUrlChange: (baseUrl: string) => void;
  onEmbeddingModelChange: (model: string) => void;
  onEmbeddingDimensionChange: (dimension: number) => void;
  onEmbeddingApiKeyChange: (apiKey: string) => void;
  onEmbeddingBaseUrlChange: (baseUrl: string) => void;
  onUseSameLlmConfigChange: (useSame: boolean) => void;
  // 测试状态回调
  onLlmTestStatusChange: (passed: boolean) => void;
  onEmbeddingTestStatusChange: (passed: boolean) => void;
}

export function ApiConfigStep({
  provider,
  apiKey,
  model,
  baseUrl,
  embeddingModel,
  embeddingDimension,
  embeddingApiKey,
  embeddingBaseUrl,
  useSameLlmConfig,
  onProviderChange,
  onApiKeyChange,
  onModelChange,
  onBaseUrlChange,
  onEmbeddingModelChange,
  onEmbeddingDimensionChange,
  onEmbeddingApiKeyChange,
  onEmbeddingBaseUrlChange,
  onUseSameLlmConfigChange,
  onLlmTestStatusChange,
  onEmbeddingTestStatusChange,
}: ApiConfigStepProps) {
  const [showKey, setShowKey] = useState(false);
  const [showEmbeddingKey, setShowEmbeddingKey] = useState(false);
  const [llmTestStatus, setLlmTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [embeddingTestStatus, setEmbeddingTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [manualInput, setManualInput] = useState(false);
  const [modelPopoverOpen, setModelPopoverOpen] = useState(false);

  // 加载 providers 列表
  useEffect(() => {
    getProviders().then(setProviders).catch(console.error);
  }, []);

  // 当 provider 变化时加载 models
  useEffect(() => {
    if (!provider || provider === "custom") {
      setModels([]);
      return;
    }

    setIsLoadingModels(true);
    getProviderModels(provider)
      .then((data) => {
        setModels(data);
        // 如果当前 model 不在列表中，选择第一个
        if (data.length > 0 && !data.find((m) => m.id === model)) {
          onModelChange(data[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setIsLoadingModels(false));
  }, [provider]);

  const currentProvider = providers.find((p) => p.id === provider);

  const handleProviderChange = (newProvider: string) => {
    onProviderChange(newProvider);
    const providerConfig = providers.find((p) => p.id === newProvider);
    if (providerConfig?.base_url) {
      onBaseUrlChange(providerConfig.base_url);
    }
    // model 会在 useEffect 中自动更新
    onModelChange("");
  };

  const testLlmConnection = async () => {
    if (!apiKey) return;

    setLlmTestStatus("testing");
    try {
      const testUrl = baseUrl || currentProvider?.base_url || "";
      const response = await fetch(`${testUrl}/models`, {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      const passed = response.ok;
      setLlmTestStatus(passed ? "success" : "error");
      onLlmTestStatusChange(passed);
    } catch {
      setLlmTestStatus("error");
      onLlmTestStatusChange(false);
    }
  };

  const testEmbeddingConnection = async () => {
    const effectiveApiKey = useSameLlmConfig ? apiKey : embeddingApiKey;
    const effectiveBaseUrl = useSameLlmConfig ? (baseUrl || currentProvider?.base_url || "") : (embeddingBaseUrl || "");
    
    if (!effectiveApiKey || !embeddingModel) return;

    setEmbeddingTestStatus("testing");
    try {
      // 测试 embedding 端点
      const response = await fetch(`${effectiveBaseUrl}/embeddings`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${effectiveApiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: embeddingModel,
          input: "test",
        }),
      });
      const passed = response.ok;
      setEmbeddingTestStatus(passed ? "success" : "error");
      onEmbeddingTestStatusChange(passed);
    } catch {
      setEmbeddingTestStatus("error");
      onEmbeddingTestStatusChange(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">配置 LLM 服务</h2>
        <p className="text-zinc-400">配置 AI 模型的 API 连接</p>
      </div>

      <div className="max-w-md mx-auto space-y-6 mt-8">
        {/* Provider */}
        <div className="space-y-2">
          <Label className="text-zinc-300">LLM 提供商</Label>
          <Select value={provider} onValueChange={handleProviderChange}>
            <SelectTrigger className="w-full bg-zinc-900 border-zinc-800 text-white">
              <SelectValue placeholder="选择提供商" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-900 border-zinc-800">
              {providers.map((p) => (
                <SelectItem key={p.id} value={p.id} className="text-zinc-200">
                  {p.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Base URL (custom only) */}
        {provider === "custom" && (
          <div className="space-y-2">
            <Label className="text-zinc-300">Base URL</Label>
            <Input
              value={baseUrl || ""}
              onChange={(e) => onBaseUrlChange(e.target.value)}
              placeholder="https://api.example.com/v1"
              className="bg-zinc-900 border-zinc-800 text-white"
            />
          </div>
        )}

        {/* API Key */}
        <div className="space-y-2">
          <Label className="text-zinc-300">API Key</Label>
          <div className="relative">
            <Input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => onApiKeyChange(e.target.value)}
              placeholder="sk-..."
              className="bg-zinc-900 border-zinc-800 text-white pr-20"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="p-1.5 text-zinc-500 hover:text-zinc-300"
              >
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </div>

        {/* Model */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-zinc-300">模型</Label>
            <div className="flex items-center gap-2">
              {isLoadingModels && (
                <span className="text-xs text-zinc-500 flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  加载中...
                </span>
              )}
              <button
                type="button"
                onClick={() => setManualInput(!manualInput)}
                className="text-xs text-violet-400 hover:text-violet-300"
              >
                {manualInput ? "从列表选择" : "手动输入"}
              </button>
            </div>
          </div>
          {manualInput || models.length === 0 ? (
            <Input
              value={model}
              onChange={(e) => onModelChange(e.target.value)}
              placeholder="输入模型 ID，如 deepseek-chat"
              className="w-full bg-zinc-900 border-zinc-800 text-white font-mono text-sm"
            />
          ) : (
            <Popover open={modelPopoverOpen} onOpenChange={setModelPopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={modelPopoverOpen}
                  className="w-full justify-between bg-zinc-900 border-zinc-800 text-white hover:bg-zinc-800 hover:text-white"
                >
                  {model ? (
                    <span className="truncate">
                      {models.find((m) => m.id === model)?.name || model}
                    </span>
                  ) : (
                    <span className="text-zinc-500">搜索或选择模型...</span>
                  )}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0 bg-zinc-900 border-zinc-800" align="start">
                <Command className="bg-zinc-900">
                  <CommandInput 
                    placeholder="搜索模型..." 
                    className="text-white placeholder:text-zinc-500"
                  />
                  <CommandList>
                    <CommandEmpty className="text-zinc-500">未找到模型</CommandEmpty>
                    <CommandGroup>
                      {models.map((m) => (
                        <CommandItem
                          key={m.id}
                          value={m.id}
                          onSelect={(value) => {
                            onModelChange(value);
                            setModelPopoverOpen(false);
                          }}
                          className="text-zinc-200 cursor-pointer hover:bg-zinc-800"
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              model === m.id ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <span className="truncate">{m.name}</span>
                            {m.reasoning && (
                              <span className="px-1.5 py-0.5 text-[10px] bg-violet-500/20 text-violet-300 rounded shrink-0">
                                <Sparkles className="inline h-2.5 w-2.5 mr-0.5" />
                                推理
                              </span>
                            )}
                            {m.tool_call && (
                              <span className="px-1.5 py-0.5 text-[10px] bg-emerald-500/20 text-emerald-300 rounded shrink-0">
                                <Zap className="inline h-2.5 w-2.5 mr-0.5" />
                                工具
                              </span>
                            )}
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          )}
          <p className="text-xs text-zinc-500">
            {manualInput ? (
              "手动输入模型 ID"
            ) : (
              <>模型列表来自 <span className="text-violet-400">models.dev</span>，如未找到可手动输入</>
            )}
          </p>
        </div>

        {/* Test LLM Connection */}
        <div className="pt-4">
          <Button
            onClick={testLlmConnection}
            disabled={!apiKey || llmTestStatus === "testing"}
            variant="outline"
            className="w-full border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            {llmTestStatus === "testing" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                测试 LLM 中...
              </>
            ) : llmTestStatus === "success" ? (
              <>
                <CheckCircle className="mr-2 h-4 w-4 text-emerald-500" />
                LLM 连接成功
              </>
            ) : llmTestStatus === "error" ? (
              <>
                <XCircle className="mr-2 h-4 w-4 text-red-500" />
                LLM 连接失败
              </>
            ) : (
              "测试 LLM 连接"
            )}
          </Button>
        </div>

        {/* Embedding Configuration */}
        <div className="space-y-4 pt-6 border-t border-zinc-800">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-white">Embedding 配置</h3>
            <label className="flex items-center gap-2 text-sm text-zinc-400">
              <input
                type="checkbox"
                checked={useSameLlmConfig}
                onChange={(e) => onUseSameLlmConfigChange(e.target.checked)}
                className="rounded border-zinc-700 bg-zinc-900"
              />
              使用相同的 API 配置
            </label>
          </div>

          {/* Embedding API Key (独立配置时显示) */}
          {!useSameLlmConfig && (
            <>
              <div className="space-y-2">
                <Label className="text-zinc-300">Embedding API Key</Label>
                <div className="relative">
                  <Input
                    type={showEmbeddingKey ? "text" : "password"}
                    value={embeddingApiKey || ""}
                    onChange={(e) => onEmbeddingApiKeyChange(e.target.value)}
                    placeholder="sk-..."
                    className="bg-zinc-900 border-zinc-800 text-white pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowEmbeddingKey(!showEmbeddingKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-zinc-500 hover:text-zinc-300"
                  >
                    {showEmbeddingKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <Label className="text-zinc-300">Embedding Base URL</Label>
                <Input
                  value={embeddingBaseUrl || ""}
                  onChange={(e) => onEmbeddingBaseUrlChange(e.target.value)}
                  placeholder="https://api.example.com/v1"
                  className="bg-zinc-900 border-zinc-800 text-white"
                />
              </div>
            </>
          )}

          {/* Embedding Model */}
          <div className="space-y-2">
            <Label className="text-zinc-300">Embedding 模型</Label>
            <Input
              value={embeddingModel}
              onChange={(e) => onEmbeddingModelChange(e.target.value)}
              placeholder="如 text-embedding-3-small 或 Qwen/Qwen3-Embedding-4B"
              className="w-full bg-zinc-900 border-zinc-800 text-white font-mono text-sm"
            />
          </div>

          {/* Embedding Dimension */}
          <div className="space-y-2">
            <Label className="text-zinc-300">Embedding 维度</Label>
            <Input
              type="number"
              value={embeddingDimension}
              onChange={(e) => onEmbeddingDimensionChange(parseInt(e.target.value) || 1536)}
              placeholder="1536"
              className="w-full bg-zinc-900 border-zinc-800 text-white font-mono text-sm"
            />
            <p className="text-xs text-zinc-500">
              常见维度：text-embedding-3-small=1536；Qwen3-Embedding-4B 常用 2560（最大 2560）
            </p>
          </div>

          {/* Test Embedding Connection */}
          <Button
            onClick={testEmbeddingConnection}
            disabled={!embeddingModel || (!useSameLlmConfig && !embeddingApiKey) || (useSameLlmConfig && !apiKey) || embeddingTestStatus === "testing"}
            variant="outline"
            className="w-full border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            {embeddingTestStatus === "testing" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                测试 Embedding 中...
              </>
            ) : embeddingTestStatus === "success" ? (
              <>
                <CheckCircle className="mr-2 h-4 w-4 text-emerald-500" />
                Embedding 连接成功
              </>
            ) : embeddingTestStatus === "error" ? (
              <>
                <XCircle className="mr-2 h-4 w-4 text-red-500" />
                Embedding 连接失败
              </>
            ) : (
              "测试 Embedding 连接"
            )}
          </Button>
        </div>

        {/* Status Summary */}
        {(llmTestStatus === "success" || embeddingTestStatus === "success") && (
          <div className="pt-4 border-t border-zinc-800">
            <div className="flex items-center gap-4 text-sm">
              <span className={llmTestStatus === "success" ? "text-emerald-400" : "text-zinc-500"}>
                LLM: {llmTestStatus === "success" ? "✓" : "○"}
              </span>
              <span className={embeddingTestStatus === "success" ? "text-emerald-400" : "text-zinc-500"}>
                Embedding: {embeddingTestStatus === "success" ? "✓" : "○"}
              </span>
              {llmTestStatus === "success" && embeddingTestStatus === "success" && (
                <span className="text-emerald-400 font-medium ml-auto">全部通过 ✓</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
