"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Database,
  Plus,
  RefreshCw,
  Edit,
  Trash2,
  Copy,
  Check,
  X,
  Link2,
  Settings2,
  Search,
  Bot,
} from "lucide-react";
import { PageHeader } from "@/components/admin";
import { getAgentTypeLabel } from "@/lib/config/labels";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  getKnowledgeConfigs,
  createKnowledgeConfig,
  updateKnowledgeConfig,
  deleteKnowledgeConfig,
  getAgents,
  type KnowledgeConfig,
  type Agent,
} from "@/lib/api/agents";

const KNOWLEDGE_TYPES = [
  { value: "faq", label: "FAQ 问答库" },
  { value: "vector", label: "向量检索" },
  { value: "graph", label: "知识图谱" },
  { value: "product", label: "商品库" },
  { value: "http_api", label: "外部 API" },
  { value: "mixed", label: "混合" },
];

function TypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    faq: "bg-blue-100 text-blue-700",
    vector: "bg-purple-100 text-purple-700",
    graph: "bg-green-100 text-green-700",
    product: "bg-amber-100 text-amber-700",
    http_api: "bg-pink-100 text-pink-700",
    mixed: "bg-zinc-100 text-zinc-700",
  };
  return (
    <Badge className={`${colors[type] || colors.mixed} hover:${colors[type] || colors.mixed}`}>
      {KNOWLEDGE_TYPES.find((t) => t.value === type)?.label || type}
    </Badge>
  );
}

function StatusBadge({ enabled }: { enabled: boolean }) {
  return enabled ? (
    <Badge variant="default" className="bg-green-100 text-green-700 hover:bg-green-100">
      <Check className="mr-1 h-3 w-3" />
      启用
    </Badge>
  ) : (
    <Badge variant="secondary" className="bg-zinc-100 text-zinc-500">
      <X className="mr-1 h-3 w-3" />
      禁用
    </Badge>
  );
}

export default function KnowledgePage() {
  const [configs, setConfigs] = useState<KnowledgeConfig[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选状态
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  // 编辑状态
  const [editingConfig, setEditingConfig] = useState<KnowledgeConfig | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [activeTab, setActiveTab] = useState("basic");

  // 详情查看
  const [selectedConfig, setSelectedConfig] = useState<KnowledgeConfig | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // 表单状态
  const [formData, setFormData] = useState({
    name: "",
    type: "vector",
    index_name: "",
    collection_name: "",
    embedding_model: "",
    top_k: 10,
    similarity_threshold: 0.5,
    rerank_enabled: false,
    filters: "",
  });

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [configsData, agentsData] = await Promise.all([
        getKnowledgeConfigs({ limit: 100 }),
        getAgents({ limit: 100 }),
      ]);
      setConfigs(configsData);
      setAgents(agentsData.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 过滤后的配置
  const filteredConfigs = configs.filter((config) => {
    const matchesSearch = !searchQuery || 
      config.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      config.collection_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = typeFilter === "all" || config.type === typeFilter;
    return matchesSearch && matchesType;
  });

  // 获取使用某配置的 Agent 列表
  const getLinkedAgents = (configId: string) => {
    return agents.filter((a) => a.knowledge_config_id === configId);
  };

  const handleCreate = () => {
    setIsCreating(true);
    setEditingConfig(null);
    setFormData({
      name: "",
      type: "vector",
      index_name: "",
      collection_name: "",
      embedding_model: "",
      top_k: 10,
      similarity_threshold: 0.5,
      rerank_enabled: false,
      filters: "",
    });
    setActiveTab("basic");
    setIsSheetOpen(true);
  };

  const handleEdit = (config: KnowledgeConfig) => {
    setIsCreating(false);
    setEditingConfig(config);
    setFormData({
      name: config.name,
      type: config.type,
      index_name: config.index_name || "",
      collection_name: config.collection_name || "",
      embedding_model: config.embedding_model || "",
      top_k: config.top_k,
      similarity_threshold: config.similarity_threshold ?? 0.5,
      rerank_enabled: config.rerank_enabled,
      filters: config.filters ? JSON.stringify(config.filters, null, 2) : "",
    });
    setActiveTab("basic");
    setIsSheetOpen(true);
  };

  const handleCopy = (config: KnowledgeConfig) => {
    setIsCreating(true);
    setEditingConfig(null);
    setFormData({
      name: `${config.name} (副本)`,
      type: config.type,
      index_name: config.index_name || "",
      collection_name: config.collection_name || "",
      embedding_model: config.embedding_model || "",
      top_k: config.top_k,
      similarity_threshold: config.similarity_threshold ?? 0.5,
      rerank_enabled: config.rerank_enabled,
      filters: config.filters ? JSON.stringify(config.filters, null, 2) : "",
    });
    setActiveTab("basic");
    setIsSheetOpen(true);
  };

  const handleViewDetail = (config: KnowledgeConfig) => {
    setSelectedConfig(config);
    setIsDetailOpen(true);
  };

  const handleSave = async () => {
    try {
      let filters = null;
      if (formData.filters) {
        try {
          filters = JSON.parse(formData.filters);
        } catch {
          setError("Filters JSON 格式错误");
          return;
        }
      }

      const data = {
        name: formData.name,
        type: formData.type as KnowledgeConfig["type"],
        index_name: formData.index_name || null,
        collection_name: formData.collection_name || null,
        embedding_model: formData.embedding_model || null,
        top_k: formData.top_k,
        similarity_threshold: formData.similarity_threshold,
        rerank_enabled: formData.rerank_enabled,
        filters,
      };

      if (isCreating) {
        await createKnowledgeConfig(data);
      } else if (editingConfig) {
        await updateKnowledgeConfig(editingConfig.id, data);
      }
      setIsSheetOpen(false);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    }
  };

  const handleDelete = async (configId: string) => {
    const linkedAgents = getLinkedAgents(configId);
    if (linkedAgents.length > 0) {
      alert(`无法删除：有 ${linkedAgents.length} 个 Agent 正在使用此配置`);
      return;
    }
    if (!confirm("确定要删除这个知识库配置吗？")) return;
    try {
      await deleteKnowledgeConfig(configId);
      loadData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  };

  if (isLoading && configs.length === 0) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="知识库管理" description="知识源配置与 Agent 绑定" />
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadData}>
            <RefreshCw className="mr-2 h-4 w-4" />
            刷新
          </Button>
          <Button size="sm" onClick={handleCreate}>
            <Plus className="mr-2 h-4 w-4" />
            新建配置
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-red-600 dark:bg-red-900/20 dark:text-red-400">
          {error}
          <Button variant="ghost" size="sm" className="ml-2" onClick={() => setError(null)}>
            关闭
          </Button>
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">配置总数</p>
                <p className="text-2xl font-bold">{configs.length}</p>
              </div>
              <Database className="h-8 w-8 text-zinc-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">向量类型</p>
                <p className="text-2xl font-bold text-purple-600">
                  {configs.filter((c) => c.type === "vector").length}
                </p>
              </div>
              <Database className="h-8 w-8 text-purple-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">FAQ 类型</p>
                <p className="text-2xl font-bold text-blue-600">
                  {configs.filter((c) => c.type === "faq").length}
                </p>
              </div>
              <Database className="h-8 w-8 text-blue-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-zinc-500">已绑定 Agent</p>
                <p className="text-2xl font-bold">
                  {agents.filter((a) => a.knowledge_config_id).length}
                </p>
              </div>
              <Link2 className="h-8 w-8 text-zinc-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 筛选栏 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="w-64">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
                <Input
                  placeholder="搜索名称或集合..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                {/* SelectItem 不能使用空字符串作为 value，因为 Radix UI 使用空字符串来清空选择 */}
                <SelectItem value="all">全部类型</SelectItem>
                {KNOWLEDGE_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 配置列表 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead className="w-[120px]">类型</TableHead>
                <TableHead>集合/索引</TableHead>
                <TableHead className="w-[80px]">Top K</TableHead>
                <TableHead className="w-[80px]">Rerank</TableHead>
                <TableHead className="w-[100px]">关联 Agent</TableHead>
                <TableHead className="w-[120px]">数据版本</TableHead>
                <TableHead className="w-[140px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConfigs.map((config) => {
                const linkedAgents = getLinkedAgents(config.id);
                return (
                  <TableRow key={config.id}>
                    <TableCell className="font-medium">
                      <button
                        className="text-left hover:underline"
                        onClick={() => handleViewDetail(config)}
                      >
                        {config.name}
                      </button>
                    </TableCell>
                    <TableCell>
                      <TypeBadge type={config.type} />
                    </TableCell>
                    <TableCell>
                      <code className="text-xs text-zinc-500">
                        {config.collection_name || config.index_name || "-"}
                      </code>
                    </TableCell>
                    <TableCell>{config.top_k}</TableCell>
                    <TableCell>
                      <StatusBadge enabled={config.rerank_enabled} />
                    </TableCell>
                    <TableCell>
                      {linkedAgents.length > 0 ? (
                        <Badge variant="outline" className="text-xs">
                          <Bot className="mr-1 h-3 w-3" />
                          {linkedAgents.length}
                        </Badge>
                      ) : (
                        <span className="text-xs text-zinc-400">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <code className="text-xs text-zinc-500">
                        {config.data_version || "-"}
                      </code>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleEdit(config)}
                          title="编辑"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleCopy(config)}
                          title="复制"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500 hover:text-red-600"
                          onClick={() => handleDelete(config.id)}
                          title="删除"
                          disabled={linkedAgents.length > 0}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {filteredConfigs.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} className="py-8 text-center text-zinc-500">
                    暂无数据
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 编辑 Sheet */}
      <Sheet open={isSheetOpen} onOpenChange={setIsSheetOpen}>
        <SheetContent className="w-[600px] sm:max-w-[600px]">
          <SheetHeader>
            <SheetTitle>{isCreating ? "新建知识库配置" : "编辑知识库配置"}</SheetTitle>
            <SheetDescription>
              {isCreating ? "创建一个新的知识源配置" : "修改知识源配置信息"}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="basic">基础信息</TabsTrigger>
                <TabsTrigger value="retrieval">检索参数</TabsTrigger>
                <TabsTrigger value="filters">Filters</TabsTrigger>
              </TabsList>
              <TabsContent value="basic" className="mt-4 space-y-4">
                <div>
                  <Label>名称 *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="配置名称"
                  />
                </div>
                <div>
                  <Label>类型 *</Label>
                  <Select
                    value={formData.type}
                    onValueChange={(v) => setFormData({ ...formData, type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {KNOWLEDGE_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>集合名称</Label>
                  <Input
                    value={formData.collection_name}
                    onChange={(e) => setFormData({ ...formData, collection_name: e.target.value })}
                    placeholder="Qdrant collection name"
                  />
                </div>
                <div>
                  <Label>索引名称</Label>
                  <Input
                    value={formData.index_name}
                    onChange={(e) => setFormData({ ...formData, index_name: e.target.value })}
                    placeholder="Index name"
                  />
                </div>
                <div>
                  <Label>嵌入模型</Label>
                  <Input
                    value={formData.embedding_model}
                    onChange={(e) => setFormData({ ...formData, embedding_model: e.target.value })}
                    placeholder="Embedding model ID"
                  />
                </div>
              </TabsContent>
              <TabsContent value="retrieval" className="mt-4 space-y-4">
                <div>
                  <Label>Top K</Label>
                  <Input
                    type="number"
                    value={formData.top_k}
                    onChange={(e) => setFormData({ ...formData, top_k: parseInt(e.target.value) || 10 })}
                    min={1}
                    max={100}
                  />
                  <p className="mt-1 text-xs text-zinc-500">检索返回的最大结果数</p>
                </div>
                <div>
                  <Label>相似度阈值</Label>
                  <Input
                    type="number"
                    value={formData.similarity_threshold}
                    onChange={(e) => setFormData({ ...formData, similarity_threshold: parseFloat(e.target.value) || 0.5 })}
                    min={0}
                    max={1}
                    step={0.1}
                  />
                  <p className="mt-1 text-xs text-zinc-500">低于此阈值的结果将被过滤</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="rerank"
                    checked={formData.rerank_enabled}
                    onChange={(e) => setFormData({ ...formData, rerank_enabled: e.target.checked })}
                    className="h-4 w-4"
                  />
                  <Label htmlFor="rerank">启用 Rerank 重排序</Label>
                </div>
              </TabsContent>
              <TabsContent value="filters" className="mt-4 space-y-4">
                <div>
                  <Label>Filters (JSON)</Label>
                  <Textarea
                    value={formData.filters}
                    onChange={(e) => setFormData({ ...formData, filters: e.target.value })}
                    placeholder='{"field": "value"}'
                    rows={10}
                    className="font-mono text-sm"
                  />
                  <p className="mt-1 text-xs text-zinc-500">
                    额外的检索过滤条件，JSON 格式
                  </p>
                </div>
              </TabsContent>
            </Tabs>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsSheetOpen(false)}>
                取消
              </Button>
              <Button onClick={handleSave}>保存</Button>
            </div>
          </div>
        </SheetContent>
      </Sheet>

      {/* 详情 Sheet */}
      <Sheet open={isDetailOpen} onOpenChange={setIsDetailOpen}>
        <SheetContent className="w-[600px] sm:max-w-[600px]">
          {selectedConfig && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedConfig.name}</SheetTitle>
                <SheetDescription>
                  <TypeBadge type={selectedConfig.type} />
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                {/* 基础信息 */}
                <div>
                  <h4 className="mb-3 font-medium flex items-center gap-2">
                    <Settings2 className="h-4 w-4" />
                    基础信息
                  </h4>
                  <div className="space-y-2 rounded-lg bg-zinc-50 p-4 dark:bg-zinc-900">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">ID</span>
                      <code className="text-xs">{selectedConfig.id}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">集合</span>
                      <code className="text-xs">{selectedConfig.collection_name || "-"}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">索引</span>
                      <code className="text-xs">{selectedConfig.index_name || "-"}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">嵌入模型</span>
                      <code className="text-xs">{selectedConfig.embedding_model || "-"}</code>
                    </div>
                  </div>
                </div>

                {/* 检索参数 */}
                <div>
                  <h4 className="mb-3 font-medium">检索参数</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-lg border p-3 text-center">
                      <div className="text-2xl font-bold">{selectedConfig.top_k}</div>
                      <div className="text-xs text-zinc-500">Top K</div>
                    </div>
                    <div className="rounded-lg border p-3 text-center">
                      <div className="text-2xl font-bold">
                        {selectedConfig.similarity_threshold ?? "-"}
                      </div>
                      <div className="text-xs text-zinc-500">阈值</div>
                    </div>
                    <div className="rounded-lg border p-3 text-center">
                      <StatusBadge enabled={selectedConfig.rerank_enabled} />
                      <div className="mt-1 text-xs text-zinc-500">Rerank</div>
                    </div>
                  </div>
                </div>

                {/* 关联 Agents */}
                <div>
                  <h4 className="mb-3 font-medium flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    关联 Agent ({getLinkedAgents(selectedConfig.id).length})
                  </h4>
                  {getLinkedAgents(selectedConfig.id).length > 0 ? (
                    <div className="space-y-2">
                      {getLinkedAgents(selectedConfig.id).map((agent) => (
                        <div
                          key={agent.id}
                          className="flex items-center justify-between rounded-lg border p-3"
                        >
                          <div>
                            <div className="font-medium">{agent.name}</div>
                            <div className="text-xs text-zinc-500">{getAgentTypeLabel(agent.type)}</div>
                          </div>
                          <Badge variant={agent.status === "enabled" ? "default" : "secondary"}>
                            {agent.status}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-lg bg-zinc-50 p-4 text-center text-zinc-500 dark:bg-zinc-900">
                      暂无 Agent 使用此配置
                    </div>
                  )}
                </div>

                {/* 版本信息 */}
                <div>
                  <h4 className="mb-3 font-medium">版本信息</h4>
                  <div className="space-y-2 rounded-lg bg-zinc-50 p-4 dark:bg-zinc-900">
                    <div className="flex justify-between">
                      <span className="text-zinc-500">数据版本</span>
                      <code className="text-xs">{selectedConfig.data_version || "-"}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">指纹</span>
                      <code className="text-xs">{selectedConfig.fingerprint || "-"}</code>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500">更新时间</span>
                      <span className="text-xs">
                        {new Date(selectedConfig.updated_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setIsDetailOpen(false)}>
                    关闭
                  </Button>
                  <Button onClick={() => {
                    setIsDetailOpen(false);
                    handleEdit(selectedConfig);
                  }}>
                    编辑
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
