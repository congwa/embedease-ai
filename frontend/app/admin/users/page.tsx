"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw, MessageSquare } from "lucide-react";
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
import {
  getUsers,
  type UserListItem,
  type PaginatedResponse,
} from "@/lib/api/admin";

export default function UsersPage() {
  const router = useRouter();
  const [data, setData] = useState<PaginatedResponse<UserListItem> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getUsers({ page, page_size: 20 });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="用户管理"
        description={`共 ${data?.total || 0} 个用户`}
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
              <TableHead>用户 ID</TableHead>
              <TableHead className="text-right">会话数</TableHead>
              <TableHead>注册时间</TableHead>
              <TableHead className="w-[100px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={4} className="h-32 text-center">
                  <div className="flex items-center justify-center">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
                  </div>
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-32 text-center text-zinc-500">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <code className="rounded bg-zinc-100 px-2 py-1 text-sm dark:bg-zinc-800">
                      {user.id}
                    </code>
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge variant="secondary">
                      <MessageSquare className="mr-1 h-3 w-3" />
                      {user.conversation_count}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-zinc-500">
                    {new Date(user.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => router.push(`/admin/conversations?user_id=${user.id}`)}
                    >
                      查看会话
                    </Button>
                  </TableCell>
                </TableRow>
              ))
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
