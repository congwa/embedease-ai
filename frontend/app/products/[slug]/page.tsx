import Link from "next/link";
import { notFound } from "next/navigation";
import { headers } from "next/headers";
import { ArrowLeft, Package } from "lucide-react";

export const dynamic = "force-dynamic";

type ProductPublicDetail = {
  id: string;
  name: string;
  summary: string | null;
  description: string | null;
  price: number | null;
  category: string | null;
  brand: string | null;
  url: string | null;
  tags: string[];
  image_urls: string[];
  specs: Record<string, string>;
};

async function fetchProductBySlug(slug: string): Promise<ProductPublicDetail | null> {
  const h = await headers();
  const host = h.get("host") || "localhost:3000";
  const proto = h.get("x-forwarded-proto") || "http";
  const res = await fetch(
    `${proto}://${host}/api/v1/products/by-slug/${encodeURIComponent(slug)}`,
    { cache: "no-store" }
  );
  if (res.status === 404) return null;
  if (!res.ok) return null;
  return res.json() as Promise<ProductPublicDetail>;
}

function formatPrice(price: number | null): string {
  if (price == null || Number.isNaN(price)) return "价格待定";
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(price);
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await fetchProductBySlug(slug);
  if (!product) notFound();

  const hero = product.image_urls.find((u) => /^https?:\/\//i.test(u));

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-50">
      <header className="border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
        <div className="mx-auto flex h-14 max-w-3xl items-center gap-3 px-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <article className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="relative aspect-[16/10] w-full bg-zinc-100 dark:bg-zinc-800">
            {hero ? (
              // eslint-disable-next-line @next/next/no-img-element -- 外链占位图，避免配置远程域名
              <img src={hero} alt="" className="absolute inset-0 h-full w-full object-cover" />
            ) : (
              <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-2 text-zinc-400">
                <Package className="h-12 w-12" />
                <span className="text-sm">暂无图片</span>
              </div>
            )}
          </div>

          <div className="space-y-5 p-6 sm:p-8">
            <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
              {product.brand ? (
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">{product.brand}</span>
              ) : null}
              {product.category ? (
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">{product.category}</span>
              ) : null}
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300">
                {product.id}
              </span>
            </div>

            <div>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{product.name}</h1>
              {product.summary ? (
                <p className="mt-2 text-base text-zinc-600 dark:text-zinc-400">{product.summary}</p>
              ) : null}
            </div>

            <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{formatPrice(product.price)}</p>

            {product.tags.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {product.tags.map((t) => (
                  <span
                    key={t}
                    className="rounded-md border border-zinc-200 bg-zinc-50 px-2 py-1 text-xs dark:border-zinc-700 dark:bg-zinc-800"
                  >
                    {t}
                  </span>
                ))}
              </div>
            ) : null}

            {Object.keys(product.specs).length > 0 ? (
              <section>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">规格参数</h2>
                <dl className="grid gap-2 sm:grid-cols-2">
                  {Object.entries(product.specs).map(([k, v]) => (
                    <div
                      key={k}
                      className="flex justify-between gap-4 rounded-lg border border-zinc-100 bg-zinc-50/80 px-3 py-2 text-sm dark:border-zinc-800 dark:bg-zinc-800/50"
                    >
                      <dt className="text-zinc-500">{k}</dt>
                      <dd className="font-medium text-right text-zinc-800 dark:text-zinc-200">{v}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            ) : null}

            {product.description ? (
              <section>
                <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500">商品介绍</h2>
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">
                  {product.description}
                </div>
              </section>
            ) : null}

            <div className="flex flex-col gap-3 border-t border-zinc-100 pt-6 dark:border-zinc-800 sm:flex-row sm:items-center">
              <Link
                href="/chat"
                className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-zinc-300 text-sm font-semibold text-zinc-800 transition hover:bg-zinc-50 dark:border-zinc-600 dark:text-zinc-100 dark:hover:bg-zinc-800 sm:max-w-md"
              >
                咨询助手
              </Link>
            </div>
          </div>
        </article>
      </main>
    </div>
  );
}
