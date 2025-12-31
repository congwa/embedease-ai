import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // SSE（/api/v1/chat）通过 Next Route Handler 透传流，避免 rewrites 代理可能造成的缓冲。
  // 其他 API 仍然使用 rewrites 代理到后端。
  compress: false,
  // 统一通过 Next 代理后端 API：
  // - 前端只请求同源 /api/v1/*
  // - rewrites 将请求转发到本机后端（默认 127.0.0.1:8000）
  // - 解决通过局域网访问前端时，浏览器把 localhost 指向“访问设备自身”导致 Failed to fetch
  async rewrites() {
    const target = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
    return [
      {
        // /api/v1/chat 由 app/api/v1/chat/route.ts 处理（SSE 透传）
        source: "/api/v1/conversations/:path*",
        destination: `${target}/api/v1/conversations/:path*`,
      },
      {
        source: "/api/v1/users/:path*",
        destination: `${target}/api/v1/users/:path*`,
      },
      {
        source: "/health",
        destination: `${target}/health`,
      },
      {
        // 兜底代理：其余 /api/* 请求统一转发到后端
        source: "/api/:path*",
        destination: `${target}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
