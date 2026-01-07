"use client";

import { Bot } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

interface GreetingPreviewProps {
  title?: string;
  subtitle?: string;
  body: string;
  cta?: {
    text: string;
    payload: string;
  };
  channel?: "web" | "support" | "api";
  className?: string;
}

export function GreetingPreview({
  title,
  subtitle,
  body,
  cta,
  channel = "web",
  className,
}: GreetingPreviewProps) {
  const isWebChannel = channel === "web";

  return (
    <div className={cn("rounded-lg border bg-zinc-50 p-4 dark:bg-zinc-900", className)}>
      <div className="mb-3 flex items-center gap-2 text-xs text-zinc-500">
        <span>预览 - {channel === "web" ? "网页端" : channel === "support" ? "客服端" : "API"}</span>
      </div>

      {/* 模拟对话界面 */}
      <div className="space-y-3">
        {/* Agent 头像和消息 */}
        <div className="flex gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
            <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex-1 space-y-2">
            {/* 消息气泡 */}
            <div
              className={cn(
                "rounded-lg p-3",
                isWebChannel
                  ? "bg-white shadow-sm dark:bg-zinc-800"
                  : "border bg-white dark:bg-zinc-800"
              )}
            >
              {title && (
                <h4 className="mb-1 font-semibold text-zinc-900 dark:text-zinc-100">
                  {title}
                </h4>
              )}
              {subtitle && (
                <p className="mb-2 text-sm text-zinc-500">{subtitle}</p>
              )}
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{body || "请输入开场白内容..."}</ReactMarkdown>
              </div>

              {/* CTA 按钮 */}
              {cta && cta.text && (
                <div className="mt-3 pt-2">
                  <button
                    type="button"
                    className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                  >
                    {cta.text}
                  </button>
                </div>
              )}
            </div>

            {/* 时间戳 */}
            <div className="text-xs text-zinc-400">刚刚</div>
          </div>
        </div>
      </div>
    </div>
  );
}
