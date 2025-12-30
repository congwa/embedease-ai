"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ExternalLink, CheckCircle, XCircle, Clock, AlertTriangle } from "lucide-react";
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
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import {
  getCrawlPages,
  type CrawlPageListItem,
  type PaginatedResponse,
} from "@/lib/api/admin";
import { cn } from "@/lib/utils";

const statusConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  pending: { label: "待解析", color: "bg-zinc-500", icon: Clock },
  parsed: { label: "已解析", color: "bg-green-500", icon: CheckCircle },
  failed: { label: "解析失败", color: "bg-red-500", icon: XCircle },
  skipped: { label: "已跳过", color: "bg-zinc-400", icon: AlertTriangle },
  skipped_duplicate: { label: "重复跳过", color: "bg-zinc-400", icon: AlertTriangle },
};

export default function CrawlerPagesPage() {
  const [data, setData] = useState<PaginatedResponse<CrawlPageListItem> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getCrawlPages({
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

  const truncateUrl = (url: string, maxLength: number = 50) => {
    if (url.length <= maxLength) return url;
    return url.slice(0, maxLength) + "...";
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="页面数据"
        description={`共 ${data?.total || 0} 个页面`}
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
            <SelectItem value="pending">待解析</SelectItem>
            <SelectItem value="parsed">已解析</SelectItem>
            <SelectItem value="failed">解析失败</SelectItem>
            <SelectItem value="skipped">已跳过</SelectItem>
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
              <TableHead className="w-[350px]">URL</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>深度</TableHead>
              <TableHead>商品页</TableHead>
              <TableHead>关联商品</TableHead>
              <TableHead>爬取时间</TableHead>
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
              data?.items.map((item) => {
                const statusInfo = getStatusInfo(item.status);
                const StatusIcon = statusInfo.icon;
                return (
                  <TableRow key={item.id}>
                    <TableCell>
                      <code className="text-sm">#{item.id}</code>
                    </TableCell>
                    <TableCell>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400"
                        title={item.url}
                      >
                        <span className="truncate max-w-[300px]">
                          {truncateUrl(item.url)}
                        </span>
                        <ExternalLink className="h-3 w-3 flex-shrink-0" />
                      </a>
                    </TableCell>
                    <TableCell>
                      {item.parse_error ? (
                        <HoverCard>
                          <HoverCardTrigger>
                            <Badge className={cn("text-white cursor-help", statusInfo.color)}>
                              <StatusIcon className="mr-1 h-3 w-3" />
                              {statusInfo.label}
                            </Badge>
                          </HoverCardTrigger>
                          <HoverCardContent className="w-80">
                            <p className="text-sm text-red-600 dark:text-red-400">
                              {item.parse_error}
                            </p>
                          </HoverCardContent>
                        </HoverCard>
                      ) : (
                        <Badge className={cn("text-white", statusInfo.color)}>
                          <StatusIcon className="mr-1 h-3 w-3" />
                          {statusInfo.label}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{item.depth}</Badge>
                    </TableCell>
                    <TableCell>
                      {item.is_product_page === true ? (
                        <Badge variant="default">是</Badge>
                      ) : item.is_product_page === false ? (
                        <Badge variant="secondary">否</Badge>
                      ) : (
                        <span className="text-zinc-400">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {item.product_id ? (
                        <code className="text-xs">{item.product_id.slice(0, 8)}...</code>
                      ) : (
                        <span className="text-zinc-400">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {new Date(item.crawled_at).toLocaleString()}
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
