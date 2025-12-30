"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, CheckCircle, XCircle, Clock, Loader2 } from "lucide-react";
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
  getCrawlTasks,
  type CrawlTaskListItem,
  type PaginatedResponse,
} from "@/lib/api/admin";
import { cn } from "@/lib/utils";

const statusConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  pending: { label: "等待中", color: "bg-zinc-500", icon: Clock },
  running: { label: "运行中", color: "bg-blue-500", icon: Loader2 },
  completed: { label: "已完成", color: "bg-green-500", icon: CheckCircle },
  failed: { label: "失败", color: "bg-red-500", icon: XCircle },
  cancelled: { label: "已取消", color: "bg-zinc-400", icon: XCircle },
};

export default function CrawlerTasksPage() {
  const [data, setData] = useState<PaginatedResponse<CrawlTaskListItem> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getCrawlTasks({
        page,
        page_size: 20,
        status: status || undefined,
      });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [page, status]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getStatusInfo = (s: string) => {
    return statusConfig[s] || statusConfig.pending;
  };

  const formatDuration = (start: string | null, end: string | null) => {
    if (!start) return "-";
    const startTime = new Date(start).getTime();
    const endTime = end ? new Date(end).getTime() : Date.now();
    const duration = Math.round((endTime - startTime) / 1000);
    if (duration < 60) return `${duration}秒`;
    if (duration < 3600) return `${Math.round(duration / 60)}分钟`;
    return `${Math.round(duration / 3600)}小时`;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="任务列表"
        description={`共 ${data?.total || 0} 个任务`}
        actions={
          <Button variant="outline" size="icon" onClick={loadData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

      {/* 筛选栏 */}
      <div className="flex items-center gap-3">
        <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="全部状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部状态</SelectItem>
            <SelectItem value="pending">等待中</SelectItem>
            <SelectItem value="running">运行中</SelectItem>
            <SelectItem value="completed">已完成</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
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
              <TableHead className="w-[80px]">ID</TableHead>
              <TableHead>站点</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">页面</TableHead>
              <TableHead className="text-right">商品</TableHead>
              <TableHead>耗时</TableHead>
              <TableHead>创建时间</TableHead>
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
              data?.items.map((task) => {
                const statusInfo = getStatusInfo(task.status);
                const StatusIcon = statusInfo.icon;
                return (
                  <TableRow key={task.id}>
                    <TableCell>
                      <code className="text-sm">#{task.id}</code>
                    </TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium text-zinc-900 dark:text-zinc-100">
                          {task.site_name || task.site_id}
                        </div>
                        <code className="text-xs text-zinc-500">{task.site_id}</code>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={cn("text-white", statusInfo.color)}>
                        <StatusIcon className={cn("mr-1 h-3 w-3", task.status === "running" && "animate-spin")} />
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="space-y-0.5">
                        <div className="text-sm">
                          <span className="text-green-600">{task.pages_parsed}</span>
                          <span className="text-zinc-400"> / </span>
                          <span>{task.pages_crawled}</span>
                        </div>
                        {task.pages_failed > 0 && (
                          <div className="text-xs text-red-500">
                            {task.pages_failed} 失败
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="space-y-0.5">
                        <div className="text-sm">{task.products_found} 发现</div>
                        <div className="text-xs text-zinc-500">
                          +{task.products_created} / ~{task.products_updated}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {formatDuration(task.started_at, task.finished_at)}
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {new Date(task.created_at).toLocaleString()}
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
