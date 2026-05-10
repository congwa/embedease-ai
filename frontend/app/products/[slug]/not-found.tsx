import Link from "next/link";

export default function ProductNotFound() {
  return (
    <main className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-4 px-4 py-16 text-center">
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">未找到该商品</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        请确认数据库中已有对应商品，且商品链接或 ID 与当前路径一致。
      </p>
      <Link href="/" className="text-sm text-emerald-600 underline-offset-4 hover:underline">
        返回首页
      </Link>
    </main>
  );
}
