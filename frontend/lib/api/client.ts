// HTTP 客户端

import { ApiError, type ApiErrorPayload } from "@/lib/errors";

// 默认使用同源（交给 Next rewrites 代理到后端），这样通过局域网访问前端时不会把 localhost 指向“访问设备自身”
// 如需直连后端（例如生产环境），可设置 NEXT_PUBLIC_API_URL="https://api.example.com"
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

/**
 * 解析错误响应
 */
async function parseErrorResponse(response: Response): Promise<ApiError> {
  const status = response.status;

  try {
    const json = await response.json();

    // 后端统一格式: { error: { code, message, data, timestamp } }
    if (json.error && typeof json.error === "object") {
      return new ApiError(status, json.error as ApiErrorPayload);
    }

    // FastAPI 默认格式: { detail: "..." }
    if (json.detail) {
      const message = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
      return new ApiError(status, {
        code: `http_${status}`,
        message,
      });
    }

    // 其他 JSON 格式
    return new ApiError(status, {
      code: `http_${status}`,
      message: JSON.stringify(json),
    });
  } catch {
    // 非 JSON 响应
    const text = await response.text().catch(() => "");
    return new ApiError(status, {
      code: `http_${status}`,
      message: text || `HTTP ${status}`,
    });
  }
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  // 处理 204 No Content 响应
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
