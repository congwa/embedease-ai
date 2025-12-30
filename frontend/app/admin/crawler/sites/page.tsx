"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ExternalLink } from "lucide-react";
import { PageHeader, DataTablePagination } from "@/components/admin";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/api/client";
import { cn } from "@/lib/utils";

interface CrawlSite {
  id: string;
  name: string;
  start_url: string;
  domain: string;
  status: string;
  is_spa: boolean;
  max_depth: number;
  max_pages: number;
  cron_expression: string | null;
  last_crawl_at: string | null;
  created_at: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  active: { label: "启用", variant: "default" },
  paused: { label: "暂停", variant: "secondary" },
  disabled: { label: "禁用", variant: "destructive" },
};

export default function CrawlerSitesPage() {
  const [sites, setSites] = useState<CrawlSite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await apiRequest<CrawlSite[]>("/crawler/sites");
      setSites(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getStatusInfo = (status: string) => {
    return statusConfig[status] || statusConfig.active;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="站点配置"
        description={`共 ${sites.length} 个站点`}
        actions={
          <Button variant="outline" size="icon" onClick={loadData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

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
              <TableHead>站点名称</TableHead>
              <TableHead>域名</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>类型</TableHead>
              <TableHead>深度/页数</TableHead>
              <TableHead>定时任务</TableHead>
              <TableHead>上次爬取</TableHead>
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
            ) : sites.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="h-32 text-center text-zinc-500">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              sites.map((site) => {
                const statusInfo = getStatusInfo(site.status);
                return (
                  <TableRow key={site.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-zinc-900 dark:text-zinc-100">
                          {site.name}
                        </div>
                        <code className="text-xs text-zinc-500">{site.id}</code>
                      </div>
                    </TableCell>
                    <TableCell>
                      <a
                        href={site.start_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400"
                      >
                        {site.domain}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusInfo.variant}>
                        {statusInfo.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {site.is_spa ? "SPA" : "静态"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">
                        {site.max_depth} / {site.max_pages}
                      </span>
                    </TableCell>
                    <TableCell>
                      {site.cron_expression ? (
                        <code className="text-xs">{site.cron_expression}</code>
                      ) : (
                        <span className="text-zinc-400">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {site.last_crawl_at
                        ? new Date(site.last_crawl_at).toLocaleString()
                        : "-"}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
