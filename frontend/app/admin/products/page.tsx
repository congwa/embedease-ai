"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { PageHeader, DataTablePagination } from "@/components/admin";
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
import { Badge } from "@/components/ui/badge";
import {
  getProducts,
  getCategories,
  getBrands,
  type ProductListItem,
  type PaginatedResponse,
} from "@/lib/api/admin";

export default function ProductsPage() {
  const [data, setData] = useState<PaginatedResponse<ProductListItem> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<string>("");
  const [brand, setBrand] = useState<string>("");

  const [categories, setCategories] = useState<string[]>([]);
  const [brands, setBrands] = useState<string[]>([]);

  // 加载筛选选项
  useEffect(() => {
    async function loadFilters() {
      try {
        const [cats, brds] = await Promise.all([getCategories(), getBrands()]);
        setCategories(cats);
        setBrands(brds);
      } catch (e) {
        console.error("Failed to load filters:", e);
      }
    }
    loadFilters();
  }, []);

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await getProducts({
        page,
        page_size: 20,
        category: category || undefined,
        brand: brand || undefined,
        search: search || undefined,
      });
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setIsLoading(false);
    }
  }, [page, category, brand, search]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = () => {
    setPage(1);
    loadData();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="商品管理"
        description={`共 ${data?.total || 0} 个商品`}
        actions={
          <Button variant="outline" size="icon" onClick={loadData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

      {/* 筛选栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <Input
            placeholder="搜索商品名称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="pl-9"
          />
        </div>

        <Select value={category} onValueChange={(v) => { setCategory(v); setPage(1); }}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="全部分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部分类</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={brand} onValueChange={(v) => { setBrand(v); setPage(1); }}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="全部品牌" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">全部品牌</SelectItem>
            {brands.map((b) => (
              <SelectItem key={b} value={b}>
                {b}
              </SelectItem>
            ))}
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
              <TableHead className="w-[300px]">商品名称</TableHead>
              <TableHead>分类</TableHead>
              <TableHead>品牌</TableHead>
              <TableHead className="text-right">价格</TableHead>
              <TableHead>来源站点</TableHead>
              <TableHead>更新时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center">
                  <div className="flex items-center justify-center">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-900 border-t-transparent dark:border-zinc-100" />
                  </div>
                </TableCell>
              </TableRow>
            ) : data?.items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-zinc-500">
                  暂无数据
                </TableCell>
              </TableRow>
            ) : (
              data?.items.map((product) => (
                <TableRow key={product.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium text-zinc-900 dark:text-zinc-100 line-clamp-1">
                        {product.name}
                      </div>
                      {product.summary && (
                        <div className="text-xs text-zinc-500 line-clamp-1">
                          {product.summary}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {product.category ? (
                      <Badge variant="secondary">{product.category}</Badge>
                    ) : (
                      <span className="text-zinc-400">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {product.brand || <span className="text-zinc-400">-</span>}
                  </TableCell>
                  <TableCell className="text-right">
                    {product.price ? (
                      <span className="font-medium">¥{product.price.toFixed(2)}</span>
                    ) : (
                      <span className="text-zinc-400">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {product.source_site_id ? (
                      <Badge variant="outline">{product.source_site_id}</Badge>
                    ) : (
                      <span className="text-zinc-400">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-zinc-500">
                    {new Date(product.updated_at).toLocaleString()}
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
