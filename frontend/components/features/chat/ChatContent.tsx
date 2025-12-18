"use client";

import { useRef, useState } from "react";
import { AlertCircle, ArrowUp, Square, X, Loader2, Check, XCircle, ListTree, Package } from "lucide-react";
import {
  ChatContainerContent,
  ChatContainerRoot,
} from "@/components/prompt-kit/chat-container";
import {
  Message,
  MessageContent,
} from "@/components/prompt-kit/message";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/prompt-kit/reasoning";
import {
  PromptInput,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import {
  Steps,
  StepsContent,
  StepsItem,
} from "@/components/prompt-kit/steps";
import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";
import type { ChatMessage, TimelineItem, TraceStep } from "@/hooks/use-chat";
import { ProductCard } from "./ProductCard";

interface ChatContentProps {
  title: string;
  timeline: TimelineItem[];
  isStreaming: boolean;
  error: string | null;
  onSendMessage: (content: string) => void;
  onAbortStream: () => void;
}

/** LLM 状态 Badge（永久显示在推理标题右侧） */
function LlmBadge({ message }: { message: ChatMessage }) {
  const llm = message.llm;
  if (!llm) return null;
  
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium transition-all",
        llm.status === "running" && "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
        llm.status === "success" && "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400",
        llm.status === "error" && "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400"
      )}
    >
      {llm.status === "running" && <Loader2 className="h-3 w-3 animate-spin" />}
      {llm.status === "success" && <Check className="h-3 w-3" />}
      {llm.status === "error" && <XCircle className="h-3 w-3" />}
      <span>
        {llm.status === "running" && "模型思考中…"}
        {llm.status === "success" && `思考完成${llm.elapsedMs ? ` · ${llm.elapsedMs}ms` : ""}`}
        {llm.status === "error" && "思考失败"}
      </span>
    </span>
  );
}

/** 工具摘要 Badge（显示在推理标题右侧） */
function ToolsBadge({ message }: { message: ChatMessage }) {
  const summary = message.toolsSummary;
  if (!summary) return null;
  
  const { runningCount, last } = summary;
  
  // 有正在运行的工具
  if (runningCount > 0) {
    const text = runningCount === 1 && last?.label 
      ? `${last.label}中…` 
      : `${runningCount} 个工具执行中…`;
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>{text}</span>
      </span>
    );
  }
  
  // 显示最后一个工具的完成摘要
  if (last && last.status !== "running") {
    const isError = last.status === "error";
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
          isError
            ? "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400"
            : "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400"
        )}
      >
        {isError ? <XCircle className="h-3 w-3" /> : <Check className="h-3 w-3" />}
        <span>
          {isError
            ? `${last.label}失败`
            : `${last.label}完成${last.count !== undefined ? ` · ${last.count}项` : ""}${last.elapsedMs ? ` · ${last.elapsedMs}ms` : ""}`}
        </span>
      </span>
    );
  }
  
  return null;
}

/** 运行轨迹面板（可折叠，显示所有 trace steps） */
function TracePanel({ message, isOpen, onToggle }: { message: ChatMessage; isOpen: boolean; onToggle: () => void }) {
  const trace = message.trace || [];
  
  if (trace.length === 0) return null;
  
  const renderTraceStep = (step: TraceStep, index: number) => {
    if (step.kind === "llm") {
      const icon = step.status === "running" 
        ? <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
        : step.status === "success"
          ? <Check className="h-3.5 w-3.5 text-emerald-500" />
          : <XCircle className="h-3.5 w-3.5 text-red-500" />;
      const text = step.status === "running"
        ? "LLM 调用中…"
        : step.status === "success"
          ? `LLM 调用完成${step.elapsedMs ? ` · ${step.elapsedMs}ms` : ""}`
          : `LLM 调用失败${step.error ? `: ${step.error}` : ""}`;
      return (
        <StepsItem key={step.id} className="flex items-center gap-2">
          {icon}
          <span>{text}</span>
        </StepsItem>
      );
    }
    
    if (step.kind === "tool") {
      const icon = step.status === "running"
        ? <Loader2 className="h-3.5 w-3.5 animate-spin text-zinc-500" />
        : step.status === "success"
          ? <Check className="h-3.5 w-3.5 text-emerald-500" />
          : <XCircle className="h-3.5 w-3.5 text-red-500" />;
      const text = step.status === "running"
        ? `${step.label}…`
        : step.status === "success"
          ? `${step.label}完成${step.count !== undefined ? ` · ${step.count}项` : ""}${step.elapsedMs ? ` · ${step.elapsedMs}ms` : ""}`
          : `${step.label}失败${step.error ? `: ${step.error}` : ""}`;
      return (
        <StepsItem key={step.id} className="flex items-center gap-2">
          {icon}
          <span>{text}</span>
        </StepsItem>
      );
    }
    
    if (step.kind === "products") {
      return (
        <StepsItem key={step.id} className="flex items-center gap-2">
          <Package className="h-3.5 w-3.5 text-orange-500" />
          <span>返回商品：{step.count} 项</span>
        </StepsItem>
      );
    }
    
    if (step.kind === "error") {
      return (
        <StepsItem key={step.id} className="flex items-center gap-2 text-red-500">
          <XCircle className="h-3.5 w-3.5" />
          <span>{step.message}</span>
        </StepsItem>
      );
    }
    
    return null;
  };
  
  return (
    <Steps open={isOpen} onOpenChange={onToggle} defaultOpen={false}>
      <StepsContent>
        {trace.map((step, index) => renderTraceStep(step, index))}
      </StepsContent>
    </Steps>
  );
}

export function ChatContent({
  title,
  timeline,
  isStreaming,
  error,
  onSendMessage,
  onAbortStream,
}: ChatContentProps) {
  const [prompt, setPrompt] = useState("");
  const [dismissedError, setDismissedError] = useState<string | null>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const isErrorVisible = Boolean(error) && dismissedError !== error;
  const [reasoningOpenMap, setReasoningOpenMap] = useState<Record<string, boolean>>({});
  const [traceOpenMap, setTraceOpenMap] = useState<Record<string, boolean>>({});

  // 修改：处理发送或停止
  const handleButtonClick = () => {
    if (isStreaming) {
      // 当前正在流式输出，点击则停止
      onAbortStream();
    } else {
      // 当前未发送，点击则发送
      if (!prompt.trim()) return;
      onSendMessage(prompt.trim());
      setPrompt("");
    }
  };

  return (
    <main className="flex h-screen flex-col overflow-hidden">
      {/* 顶部栏 */}
      <header className="z-10 flex h-16 w-full shrink-0 items-center gap-2 border-b border-zinc-200 bg-white px-4 dark:border-zinc-800 dark:bg-zinc-900">
        <SidebarTrigger className="-ml-1" />
        <div className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
          {title || "新对话"}
        </div>
      </header>

      {/* 消息区域 */}
      <div ref={chatContainerRef} className="relative flex-1 overflow-y-auto">
        <ChatContainerRoot className="h-full">
          <ChatContainerContent className="space-y-0 px-5 py-12">
            {timeline.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-orange-500/10">
                  <span className="text-2xl">🛒</span>
                </div>
                <h2 className="mb-2 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
                  商品推荐助手
                </h2>
                <p className="text-center text-sm text-zinc-500">
                  告诉我你想要什么，我来帮你找到最合适的商品
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {["推荐一款降噪耳机", "有什么好的跑步鞋", "想买一台破壁机"].map(
                    (suggestion) => (
                      <Button
                        key={suggestion}
                        variant="outline"
                        size="sm"
                        className="text-xs"
                        onClick={() => {
                          onSendMessage(suggestion);
                        }}
                        disabled={isStreaming}
                      >
                        {suggestion}
                      </Button>
                    )
                  )}
                </div>
              </div>
            )}

            {timeline.map((item, itemIndex) => {
              // 消息 item（timeline 现在只有消息类型）
              const message = item.message;
              const isAssistant = message.role === "assistant";
              const messageKey = message.id || `${message.role}-${itemIndex}`;
              const segments: Array<{
                id: string;
                kind: "reasoning" | "content";
                text: string;
                isOpen?: boolean;
              }> =
                Array.isArray(message.segments) && message.segments.length > 0
                  ? message.segments
                  : (() => {
                      const out: Array<{
                        id: string;
                        kind: "reasoning" | "content";
                        text: string;
                      }> = [];
                      if (message.reasoning) {
                        out.push({
                          id: `${messageKey}-reasoning-0`,
                          kind: "reasoning",
                          text: message.reasoning,
                        });
                      }
                      if (message.content) {
                        out.push({
                          id: `${messageKey}-content-0`,
                          kind: "content",
                          text: message.content,
                        });
                      }
                      return out;
                    })();

              if (!message.id) {
                console.log("[chat] message.id \u7f3a\u5931\uff0c\u5df2\u4f7f\u7528 fallback key", {
                  itemIndex,
                  role: message.role,
                });
              }

              return (
                <Message
                  key={messageKey}
                  className={cn(
                    "mx-auto flex w-full max-w-3xl flex-col gap-2 px-6",
                    isAssistant ? "items-start" : "items-end"
                  )}
                >
                  {isAssistant ? (
                    <div className="flex w-full flex-col gap-3">
                      {/* 推理块渲染：标题右侧显示轨迹入口 + LLM badge + 工具摘要 badge */}
                      {(() => {
                        const hasReasoningSegment = segments.some(s => s.kind === "reasoning");
                        const showReasoningBlock = hasReasoningSegment || message.llm;
                        const traceCount = message.trace?.length || 0;
                        const isTraceOpen = traceOpenMap[message.id] ?? false;
                        
                        const contentChars = segments
                          .filter((s) => s.kind === "content")
                          .reduce((acc, s) => acc + (s.text?.length ?? 0), 0);
                        const reasoningChars = segments
                          .filter((s) => s.kind === "reasoning")
                          .reduce((acc, s) => acc + (s.text?.length ?? 0), 0);
                        const hasMeaningfulContent = contentChars >= 80;
                        const preferShowReasoning =
                          reasoningChars > 0 && contentChars < 40 && reasoningChars > contentChars * 2;
                        const reasoningCount = segments.filter((s) => s.kind === "reasoning").length;
                        
                        return (
                          <div className="flex w-full flex-col gap-3">
                            {/* 推理块（如果有 reasoning segment 或 llm 状态） */}
                            {showReasoningBlock && (() => {
                              let reasoningIndex = 0;
                              const reasoningSegments = segments.filter(s => s.kind === "reasoning");
                              
                              // 如果没有 reasoning segment 但有 llm 状态，显示一个空的推理块
                              if (reasoningSegments.length === 0 && message.llm) {
                                return (
                                  <div key="llm-status-block">
                                    <div className="flex items-center justify-between">
                                      <span className="text-sm text-muted-foreground">推理过程</span>
                                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                        {traceCount > 0 && (
                                          <button
                                            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-zinc-100 hover:text-foreground dark:hover:bg-zinc-800"
                                            onClick={() => setTraceOpenMap(prev => ({ ...prev, [message.id]: !isTraceOpen }))}
                                          >
                                            <ListTree className="h-3 w-3" />
                                            <span>轨迹({traceCount})</span>
                                          </button>
                                        )}
                                        <LlmBadge message={message} />
                                        <ToolsBadge message={message} />
                                      </div>
                                    </div>
                                    {isTraceOpen && (
                                      <TracePanel
                                        message={message}
                                        isOpen={isTraceOpen}
                                        onToggle={() => setTraceOpenMap(prev => ({ ...prev, [message.id]: !isTraceOpen }))}
                                      />
                                    )}
                                  </div>
                                );
                              }
                              
                              return reasoningSegments.map((seg) => {
                                reasoningIndex += 1;
                                const defaultOpen = preferShowReasoning
                                  ? true
                                  : hasMeaningfulContent
                                    ? (seg.isOpen ?? false)
                                    : true;
                                const open = reasoningOpenMap[seg.id] ?? defaultOpen;
                                const isFirstReasoning = reasoningIndex === 1;
                                
                                return (
                                  <Reasoning
                                    key={seg.id}
                                    isStreaming={message.isStreaming}
                                    open={open}
                                    onOpenChange={(next) =>
                                      setReasoningOpenMap((prev) => ({
                                        ...prev,
                                        [seg.id]: next,
                                      }))
                                    }
                                  >
                                    {/* 标题行：左侧折叠按钮 + 右侧状态 badges */}
                                    <div className="flex items-center justify-between">
                                      <ReasoningTrigger>
                                        推理过程{reasoningCount > 1 ? ` ${reasoningIndex}` : ""}
                                      </ReasoningTrigger>
                                      {/* 只在第一个推理块上显示状态 badges */}
                                      {isFirstReasoning && (
                                        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                          {traceCount > 0 && (
                                            <button
                                              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-zinc-100 hover:text-foreground dark:hover:bg-zinc-800"
                                              onClick={() => setTraceOpenMap(prev => ({ ...prev, [message.id]: !isTraceOpen }))}
                                            >
                                              <ListTree className="h-3 w-3" />
                                              <span>轨迹({traceCount})</span>
                                            </button>
                                          )}
                                          <LlmBadge message={message} />
                                          <ToolsBadge message={message} />
                                        </div>
                                      )}
                                    </div>
                                    <ReasoningContent className="mt-2" markdown>
                                      {seg.text}
                                    </ReasoningContent>
                                    {/* TracePanel 放在第一个推理块下面 */}
                                    {isFirstReasoning && isTraceOpen && (
                                      <TracePanel
                                        message={message}
                                        isOpen={isTraceOpen}
                                        onToggle={() => setTraceOpenMap(prev => ({ ...prev, [message.id]: !isTraceOpen }))}
                                      />
                                    )}
                                  </Reasoning>
                                );
                              });
                            })()}
                            
                            {/* 正文内容 segments */}
                            {segments
                              .filter((seg) => seg.kind === "content")
                              .map((seg) => (
                                <MessageContent
                                  key={seg.id}
                                  className="prose flex-1 rounded-lg bg-transparent p-0 text-zinc-900 dark:text-zinc-100"
                                  markdown
                                >
                                  {seg.text}
                                </MessageContent>
                              ))}
                          </div>
                        );
                      })()}

                      {message.products && message.products.length > 0 && (
                        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          {message.products.map((product, productIndex) => {
                            const productId =
                              typeof product.id === "string" && product.id ? product.id : null;
                            const productKey = productId ?? `${messageKey}-product-${productIndex}`;
                            if (!productId) {
                              console.log("[chat] product.id \u7f3a\u5931\uff0c\u5df2\u4f7f\u7528 fallback key", {
                                messageId: message.id,
                                itemIndex,
                                productIndex,
                              });
                            }
                            return <ProductCard key={productKey} product={product} />;
                          })}
                        </div>
                      )}
                    </div>
                  ) : (
                    <MessageContent className="max-w-[85%] rounded-3xl bg-zinc-100 px-5 py-2.5 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 sm:max-w-[75%]">
                      {message.content}
                    </MessageContent>
                  )}
                </Message>
              );
            })}
          </ChatContainerContent>
          
          <div className="absolute bottom-4 left-1/2 flex w-full max-w-3xl -translate-x-1/2 justify-end px-5">
            <ScrollButton className="shadow-sm" />
          </div>
        </ChatContainerRoot>
      </div>

      {/* 输入区域 */}
      <div className="z-10 shrink-0 bg-white px-3 pb-3 dark:bg-zinc-900 md:px-5 md:pb-5">
        <div className="mx-auto max-w-3xl">
          {/* 错误提示 */}
          {error && isErrorVisible && (
            <div className="mb-3 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <button
                onClick={() => setDismissedError(error)}
                className="shrink-0 rounded p-1 hover:bg-red-100 dark:hover:bg-red-900/40"
                title="关闭错误提示"
                aria-label="关闭错误提示"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )}
          <PromptInput
            isLoading={isStreaming}
            value={prompt}
            onValueChange={setPrompt}
            onSubmit={handleButtonClick}
            className="relative z-10 w-full rounded-3xl border border-zinc-200 bg-white p-0 pt-1 shadow-sm dark:border-zinc-700 dark:bg-zinc-800"
          >
            <div className="flex flex-col">
              <PromptInputTextarea
                placeholder="描述你想要的商品..."
                className="min-h-[44px] pl-4 pt-3 text-base leading-[1.3]"
              />

              <PromptInputActions className="mt-5 flex w-full items-center justify-end gap-2 px-3 pb-3">
                <Button
                  size="icon"
                  disabled={!isStreaming && !prompt.trim()}
                  onClick={handleButtonClick}
                  className={cn(
                    "h-9 w-9 rounded-full transition-colors",
                    isStreaming && "bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700"
                  )}
                  title={isStreaming ? "停止生成" : "发送消息"}
                >
                  {isStreaming ? (
                    <Square className="h-4 w-4" />
                  ) : (
                    <ArrowUp className="h-4 w-4" />
                  )}
                </Button>
              </PromptInputActions>
            </div>
          </PromptInput>
        </div>
      </div>
    </main>
  );
}
