"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, Bot, Clock, Headphones } from "lucide-react";
import { PageHeader, DataTablePagination } from "@/components/admin";
import { Button } from "@/components/ui/button";
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
import { Badge } from "@/components/ui/badge";
import {
  getConversations,
  type ConversationListItem,
  type PaginatedResponse,
} from "@/lib/api/admin";
import { cn } from "@/lib/utils";

const stateConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  ai: { label: "AI 模式", color: "bg-blue-500", icon: Bot },
  pending: { label: "等待接入", color: "bg-yellow-500", icon: Clock },
  human: { label: "人工服务", color: "bg-green-500", icon: Headphones },
};

export default function ConversationsPage() {
  const router = useRouter();
  const [data, setData] = useState<PaginatedResponse<ConversationListItem> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [handoffState, setHandoffState] = useState<string>("");

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getConversations({
        page,
        page_size: 20,
        handoff_state: handoffState || undefined,
      });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [page, handoffState]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getStateInfo = (state: string) => {
    return stateConfig[state] || stateConfig.ai;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="会话管理"
        description={`共 ${data?.total || 0} 个会话`}
        actions={
          <Button variant="outline" size="icon" onClick={loadData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

      {/* 筛选栏 */}
      <div className="flex items-center gap-3">
        <Select value={handoffState} onValueChange={(v) => { setHandoffState(v); setPage(1); }}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            <SelectItem value="ai">AI 模式</SelectItem>
            <SelectItem value="pending">等待接入</SelectItem>
            <SelectItem value="human">人工服务</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* 表格 */}
      <div className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[250px]">会话标题</TableHead>
              <TableHead>用户 ID</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>客服</TableHead>
              <TableHead className="text-right">消息数</TableHead>
              <TableHead>创建时间</TableHead>
              <TableHead>更新时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center">
                  <div className="flex items-center justify-center">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
                  </div>
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-zinc-500">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((conv) => {
                const stateInfo = getStateInfo(conv.handoff_state);
                const StateIcon = stateInfo.icon;
                return (
                  <TableRow
                    key={conv.id}
                    className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900"
                    onClick={() => router.push(`/support/${conv.id}`)}
                  >
                    <TableCell>
                      <div className="font-medium text-zinc-900 dark:text-zinc-100 line-clamp-1">
                        {conv.title || "新会话"}
                      </div>
                    </TableCell>
                    <TableCell>
                      <code className="text-xs text-zinc-500">
                        {conv.user_id.slice(0, 8)}...
                      </code>
                    </TableCell>
                    <TableCell>
                      <Badge
                        className={cn(
                          "text-white",
                          stateInfo.color
                        )}
                      >
                        <StateIcon className="mr-1 h-3 w-3" />
                        {stateInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {conv.handoff_operator || (
                        <span className="text-zinc-400">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {conv.message_count}
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {new Date(conv.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {new Date(conv.updated_at).toLocaleString()}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* 分页 */}
      {data && data.total_pages > 1 && (
        <div className="flex justify-center">
          <DataTablePagination
            page={page}
            totalPages={data.total_pages}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
