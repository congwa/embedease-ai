"use client";

import { useParams } from "next/navigation";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge, PromptViewer } from "@/components/admin";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Brain,
  User,
  FileText,
  Network,
  ChevronDown,
  ChevronRight,
  Eye,
  RefreshCw,
} from "lucide-react";
import {
  getAgentMemoryConfig,
  previewAgentPrompt,
  getAgentUsers,
  type MemoryConfig,
  type PromptPreviewResponse,
  type AgentUserItem,
} from "@/lib/api/agents";
import {
  getUserProfile,
  getUserFacts,
  getUserGraph,
  type UserProfile,
  type FactListResponse,
  type GraphResponse,
} from "@/lib/api/users";

export default function AgentMemoryPage() {
  const params = useParams();
  const agentId = params.agentId as string;

  const [memoryConfig, setMemoryConfig] = useState<MemoryConfig | null>(null);
  const [users, setUsers] = useState<AgentUserItem[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [promptPreview, setPromptPreview] = useState<PromptPreviewResponse | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [userFacts, setUserFacts] = useState<FactListResponse | null>(null);
  const [userGraph, setUserGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMemory, setLoadingMemory] = useState(false);

  const [promptOpen, setPromptOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(true);
  const [factsOpen, setFactsOpen] = useState(true);
  const [graphOpen, setGraphOpen] = useState(true);

  useEffect(() => {
    loadInitialData();
  }, [agentId]);

  useEffect(() => {
    if (selectedUserId) {
      loadUserMemoryData(selectedUserId);
    } else {
      setUserProfile(null);
      setUserFacts(null);
      setUserGraph(null);
      setPromptPreview(null);
    }
  }, [selectedUserId]);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [config, usersData] = await Promise.all([
        getAgentMemoryConfig(agentId),
        getAgentUsers(agentId, 100),
      ]);
      setMemoryConfig(config);
      setUsers(usersData.items);

      if (usersData.items.length > 0) {
        setSelectedUserId(usersData.items[0].user_id);
      }
    } catch (error) {
      console.error("加载数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadUserMemoryData = async (userId: string) => {
    setLoadingMemory(true);
    try {
      const [profile, facts, graph, preview] = await Promise.all([
        getUserProfile(userId).catch(() => null),
        getUserFacts(userId, 50).catch(() => null),
        getUserGraph(userId).catch(() => null),
        previewAgentPrompt(agentId, { user_id: userId, mode: "natural" }).catch(() => null),
      ]);
      setUserProfile(profile);
      setUserFacts(facts);
      setUserGraph(graph);
      setPromptPreview(preview);
    } catch (error) {
      console.error("加载用户记忆数据失败:", error);
    } finally {
      setLoadingMemory(false);
    }
  };

  const handleRefresh = () => {
    if (selectedUserId) {
      loadUserMemoryData(selectedUserId);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 记忆系统配置概览 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Brain className="h-4 w-4" />
            记忆系统配置
          </CardTitle>
          <CardDescription>当前 Agent 的记忆注入配置及系统状态</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <div className="text-sm font-medium text-zinc-500">系统总开关</div>
              <StatusBadge enabled={memoryConfig?.memory_enabled ?? false} />
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-zinc-500">用户画像</div>
              <div className="flex items-center gap-2">
                <StatusBadge enabled={memoryConfig?.store_enabled ?? false} />
                {memoryConfig?.inject_profile && (
                  <Badge variant="outline" className="text-xs">
                    注入
                  </Badge>
                )}
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-zinc-500">事实记忆</div>
              <div className="flex items-center gap-2">
                <StatusBadge enabled={memoryConfig?.fact_enabled ?? false} />
                {memoryConfig?.inject_facts && (
                  <Badge variant="outline" className="text-xs">
                    注入 (最多 {memoryConfig.max_facts} 条)
                  </Badge>
                )}
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium text-zinc-500">知识图谱</div>
              <div className="flex items-center gap-2">
                <StatusBadge enabled={memoryConfig?.graph_enabled ?? false} />
                {memoryConfig?.inject_graph && (
                  <Badge variant="outline" className="text-xs">
                    注入 (最多 {memoryConfig.max_graph_entities} 实体)
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 用户选择和记忆数据 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <User className="h-4 w-4" />
                用户记忆数据
              </CardTitle>
              <CardDescription>
                选择用户查看其画像、事实记忆和知识图谱
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={selectedUserId} onValueChange={setSelectedUserId}>
                <SelectTrigger className="w-64">
                  <SelectValue placeholder="选择用户" />
                </SelectTrigger>
                <SelectContent>
                  {users.length === 0 ? (
                    <SelectItem value="_empty" disabled>
                      暂无用户数据
                    </SelectItem>
                  ) : (
                    users.map((user) => (
                      <SelectItem key={user.user_id} value={user.user_id}>
                        <span className="font-mono text-xs">{user.user_id.slice(0, 8)}...</span>
                        <span className="ml-2 text-zinc-500">
                          ({user.conversation_count} 次对话)
                        </span>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" onClick={handleRefresh} disabled={!selectedUserId}>
                <RefreshCw className={`h-4 w-4 ${loadingMemory ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {!selectedUserId ? (
            <div className="py-8 text-center text-zinc-400">请选择用户查看记忆数据</div>
          ) : loadingMemory ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-5 w-5 animate-spin text-zinc-400" />
            </div>
          ) : (
            <div className="space-y-4">
              {/* 用户画像 */}
              <Collapsible open={profileOpen} onOpenChange={setProfileOpen}>
                <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg bg-zinc-50 px-4 py-3 hover:bg-zinc-100 dark:bg-zinc-900 dark:hover:bg-zinc-800">
                  <div className="flex items-center gap-2">
                    {profileOpen ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <User className="h-4 w-4" />
                    <span className="font-medium">用户画像</span>
                  </div>
                  {userProfile?.updated_at && (
                    <span className="text-xs text-zinc-500">
                      更新于 {new Date(userProfile.updated_at).toLocaleString()}
                    </span>
                  )}
                </CollapsibleTrigger>
                <CollapsibleContent className="px-4 pt-3">
                  {userProfile ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {userProfile.nickname && (
                        <div>
                          <span className="text-sm text-zinc-500">昵称：</span>
                          <span className="ml-2">{userProfile.nickname}</span>
                        </div>
                      )}
                      {userProfile.tone_preference && (
                        <div>
                          <span className="text-sm text-zinc-500">语气偏好：</span>
                          <span className="ml-2">{userProfile.tone_preference}</span>
                        </div>
                      )}
                      {(userProfile.budget_min || userProfile.budget_max) && (
                        <div>
                          <span className="text-sm text-zinc-500">预算：</span>
                          <span className="ml-2">
                            ¥{userProfile.budget_min ?? "?"} - ¥{userProfile.budget_max ?? "?"}
                          </span>
                        </div>
                      )}
                      {userProfile.favorite_categories.length > 0 && (
                        <div className="sm:col-span-2">
                          <span className="text-sm text-zinc-500">喜好品类：</span>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {userProfile.favorite_categories.map((cat, i) => (
                              <Badge key={i} variant="secondary">
                                {cat}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                      {Object.keys(userProfile.custom_data).length > 0 && (
                        <div className="sm:col-span-2">
                          <span className="text-sm text-zinc-500">自定义数据：</span>
                          <pre className="mt-1 max-h-32 overflow-auto rounded bg-zinc-100 p-2 text-xs dark:bg-zinc-800">
                            {JSON.stringify(userProfile.custom_data, null, 2)}
                          </pre>
                        </div>
                      )}
                      {!userProfile.nickname &&
                        !userProfile.tone_preference &&
                        !userProfile.budget_min &&
                        userProfile.favorite_categories.length === 0 &&
                        Object.keys(userProfile.custom_data).length === 0 && (
                          <div className="text-sm text-zinc-400">暂无画像数据</div>
                        )}
                    </div>
                  ) : (
                    <div className="text-sm text-zinc-400">暂无画像数据</div>
                  )}
                </CollapsibleContent>
              </Collapsible>

              {/* 事实记忆 */}
              <Collapsible open={factsOpen} onOpenChange={setFactsOpen}>
                <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg bg-zinc-50 px-4 py-3 hover:bg-zinc-100 dark:bg-zinc-900 dark:hover:bg-zinc-800">
                  <div className="flex items-center gap-2">
                    {factsOpen ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <FileText className="h-4 w-4" />
                    <span className="font-medium">事实记忆</span>
                    {userFacts && (
                      <Badge variant="secondary" className="ml-2">
                        {userFacts.total} 条
                      </Badge>
                    )}
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent className="px-4 pt-3">
                  {userFacts && userFacts.items.length > 0 ? (
                    <div className="max-h-64 space-y-2 overflow-auto">
                      {userFacts.items.map((fact) => (
                        <div
                          key={fact.id}
                          className="flex items-start gap-2 rounded border p-2 text-sm dark:border-zinc-700"
                        >
                          <span className="mt-0.5 text-zinc-400">•</span>
                          <div className="flex-1">
                            <div>{fact.content}</div>
                            <div className="mt-1 text-xs text-zinc-400">
                              {new Date(fact.created_at).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-zinc-400">暂无事实记忆</div>
                  )}
                </CollapsibleContent>
              </Collapsible>

              {/* 知识图谱 */}
              <Collapsible open={graphOpen} onOpenChange={setGraphOpen}>
                <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg bg-zinc-50 px-4 py-3 hover:bg-zinc-100 dark:bg-zinc-900 dark:hover:bg-zinc-800">
                  <div className="flex items-center gap-2">
                    {graphOpen ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <Network className="h-4 w-4" />
                    <span className="font-medium">知识图谱</span>
                    {userGraph && (
                      <Badge variant="secondary" className="ml-2">
                        {userGraph.entity_count} 实体, {userGraph.relation_count} 关系
                      </Badge>
                    )}
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent className="px-4 pt-3">
                  {userGraph && userGraph.entities.length > 0 ? (
                    <div className="space-y-3">
                      <div>
                        <div className="mb-2 text-sm font-medium text-zinc-500">实体</div>
                        <div className="flex flex-wrap gap-2">
                          {userGraph.entities.map((entity, i) => (
                            <Badge key={i} variant="outline" className="font-normal">
                              <span className="text-zinc-400">[{entity.entity_type}]</span>
                              <span className="ml-1">{entity.name}</span>
                            </Badge>
                          ))}
                        </div>
                      </div>
                      {userGraph.relations.length > 0 && (
                        <div>
                          <div className="mb-2 text-sm font-medium text-zinc-500">关系</div>
                          <div className="max-h-32 space-y-1 overflow-auto">
                            {userGraph.relations.map((rel, i) => (
                              <div key={i} className="text-sm">
                                <span className="font-medium">{rel.from_entity}</span>
                                <span className="mx-2 text-zinc-400">
                                  --[{rel.relation_type}]--&gt;
                                </span>
                                <span className="font-medium">{rel.to_entity}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-zinc-400">暂无知识图谱数据</div>
                  )}
                </CollapsibleContent>
              </Collapsible>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 提示词预览 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Eye className="h-4 w-4" />
                系统提示词预览
              </CardTitle>
              <CardDescription>
                查看完整的系统提示词（含记忆注入内容）
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPromptOpen(!promptOpen)}
            >
              {promptOpen ? "收起" : "展开查看"}
            </Button>
          </div>
        </CardHeader>
        {promptOpen && (
          <CardContent className="space-y-4">
            {promptPreview ? (
              <>
                <div>
                  <div className="mb-2 text-sm font-medium text-zinc-500">基础提示词</div>
                  <PromptViewer content={promptPreview.base_prompt} maxHeight={192} />
                </div>
                {promptPreview.mode_suffix && (
                  <div>
                    <div className="mb-2 text-sm font-medium text-zinc-500">模式后缀</div>
                    <PromptViewer content={promptPreview.mode_suffix} maxHeight={128} />
                  </div>
                )}
                {promptPreview.memory_context && (
                  <div>
                    <div className="mb-2 text-sm font-medium text-zinc-500">
                      记忆注入内容
                      <Badge variant="secondary" className="ml-2">
                        动态
                      </Badge>
                    </div>
                    <PromptViewer 
                      content={promptPreview.memory_context || "(无记忆数据)"} 
                      maxHeight={192}
                      className="bg-blue-50/50 dark:bg-blue-950/30"
                    />
                  </div>
                )}
              </>
            ) : (
              <div className="py-4 text-center text-zinc-400">
                {selectedUserId ? "加载中..." : "请先选择用户以查看完整提示词预览"}
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
